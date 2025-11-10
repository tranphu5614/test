import json
import httpx
import asyncio
from AI_Interface.STT.Interface import TranscriptionResult
from AI_Interface.LLM.Interface import LanguageModelInterface, GenericAnalysisResult
from Model.tasks import LLM_TASKS

class GeminiClient(LanguageModelInterface):
    """Adapter for Google's Gemini models via REST API"""

    MAX_RETRIES = 2 # The number of times to retry after initial failure

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Google AI Studio API key is required")
        self._api_key = api_key
        self._model = model
        self._api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"

    def _format_transcript_for_prompt(self, transcript: TranscriptionResult, numbered: bool = False) -> str:
        """Formats the transcript into a human-readable string for the LLM"""
        lines = []
        for i, utterance in enumerate(transcript.utterances):
            prefix = f"Utterance {i}: Speaker: {utterance.speaker}" if numbered else f"Speaker {utterance.speaker}:"
            lines.append(f"{prefix} {utterance.text}")
        return "\n".join(lines)

    async def _make_request(self, client: httpx.AsyncClient, prompt: str) -> str:
        """Helper function to make the API call to the Gemini API"""
        current_attempt = 0
        original_prompt = prompt
        while current_attempt <= self.MAX_RETRIES:
            print(f"LLM call attempt {current_attempt + 1}...")

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }


            response = await client.post(self._api_url, json=payload, timeout=60)
            response.raise_for_status()

            # Extract the text from the nested response structure
            try:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                # Attempt to parse the JSON to validate it
                json.loads(raw_text)
                # If the above line doesn't raise error, the JSON is valid
                return raw_text

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                current_attempt += 1
                print(f"Warning: LLM response was not valid JSON. Error: {e}. Retrying({current_attempt}/{self.MAX_RETRIES})")
                if current_attempt > self.MAX_RETRIES:
                    raise RuntimeError(f"LLM failed to produce valid JSON after {self.MAX_RETRIES + 1} attempts. Last response: {raw_text}")

            # Construct a new prompt to ask the LLM to fix its mistake
            prompt = f"""
            Your previous response was not valid JSON. Please correct it.
            
            ORIGINAL REQUEST:
            ---
            {original_prompt}
            ---
            
            INVALID RESPONSE:
            ---
            {raw_text}
            ---
            
            Please provide ONLY the corrected, valid JSON object.
            """
            await asyncio.sleep(1) # Simple backoff

    async def analyze(self, transcript: TranscriptionResult, task_name: str) -> GenericAnalysisResult:
        """
        Performs a specified analysis task using a dynamically generated prompt
        based on the task registry.
        """
        # 1. Validate the task name (Guard Clause)
        if task_name not in LLM_TASKS:
            raise ValueError(f"Unknown task: '{task_name}'. Please define it in tasks.py.")

        # 2. Retrieve the task definition from the central registry
        task_definition = LLM_TASKS[task_name]
        task_description = task_definition['description']
        output_schema = task_definition['output_schema']

        # 3. Format the transcript for the prompt
        # (Using the numbered format for tasks that might need to reference specific lines)
        formatted_transcript = self._format_transcript_for_prompt(transcript, numbered=True)

        # 4. Dynamically build the prompt from the task definition
        prompt = f"""
        You are an expert analysis engine. Perform the following task:
        TASK: {task_description}

        Based on this transcript:
        ---
        {formatted_transcript}
        ---

        Your response MUST be a single, valid JSON object that strictly adheres to the following schema.
        Do not include any other text, explanations, or markdown formatting.

        JSON SCHEMA:
        {output_schema}
        """

        # 5. Delegate execution to the robust, self-correcting request method
        async with httpx.AsyncClient() as client:
            json_response_text = await self._make_request(client, prompt)

        # 6. Parse the validated JSON and return it as a generic dictionary
        return json.loads(json_response_text)