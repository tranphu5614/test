import httpx
import asyncio
import os
from AI_Interface.STT.Interface import SpeechToTextInterface, TranscriptionResult, Utterance, Word

class AssemblyAIClient(SpeechToTextInterface):
    """
    Adapter for the AssemblyAI Speech-To-Text service.
    """
    BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("AssemblyAI API key is required.")
        self._api_key = api_key
        self._headers = {
            "authorization": self._api_key,
            "content-type": "application/json"
        }

    async def _upload_local_file(self, client: httpx.AsyncClient, filepath: str) -> str:
        """Uploads a local file to AssemblyAI's secure storage."""
        print(f"Uploading file: {filepath}...")
        upload_endpoint = f"{self.BASE_URL}/upload"

        # httpx can handle async file I/O context managers
        async with await open(filepath, "rb") as f:
            response = await client.post(
                upload_endpoint,
                headers={"authorization": self._api_key},
                data=f,
                timeout=60.0
            )

        response.raise_for_status()
        return response.json()["upload_url"]

    async def _poll_for_result(self, client: httpx.AsyncClient, transcript_id: str) -> dict:
        """Polls the transcript endpoint until the job is complete."""
        polling_endpoint = f"{self.BASE_URL}/transcript/{transcript_id}"
        while True:
            response = await client.get(polling_endpoint, headers=self._headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()

            if result['status'] == 'completed':
                return result
            elif result['status'] == 'error':
                raise RuntimeError(f"Transcription failed: {result['error']}")
            else:
                print(f"STT job status: {result['status']}...")
                await asyncio.sleep(5)

    def _transform_to_generic_result(self, api_result: dict) -> TranscriptionResult:
        """Converts the AssemblyAI-specific JSON into the generic data model"""
        utterances = []
        if api_result.get("utterances"):
            for utterance_data in api_result["utterances"]:
                words = [
                    Word(
                        text=word_data['text'],
                        start=word_data['start'] / 1000.0,
                        end=word_data['end'] / 1000.0
                    ) for word_data in utterance_data['words']
                ]
                utterances.append(
                    Utterance(
                        speaker=utterance_data['speaker'],
                        start=utterance_data['start'],
                        end=utterance_data['end'],
                        text=utterance_data['text'],
                        words=words
                    )
                )
        return TranscriptionResult(
            full_text=api_result.get("text", ""),
            utterances=utterances
        )

    async def transcribe(self, audio_source: str, enable_speaker_diarization: bool = False, language: str = 'vi') -> TranscriptionResult:
        """Implementation of STT interface for AssemblyAI"""
        print("Using AssemblyAI for transcription")

        async with httpx.AsyncClient() as client:
            # 1. Determine audio source and get URL
            if os.path.exists(audio_source):
                audio_url = await self._upload_local_file(client, audio_source)
            elif audio_source.startswith(('http://', 'https://')):
                audio_url = audio_source
            else:
                raise FileNotFoundError(f"Audio source not found: {audio_source}")

            # 2. Prepare the job payload
            payload = {"audio_url": audio_url, "speaker_labels": enable_speaker_diarization}
            if language:
                payload["language_code"] = language

            # 3. Submit the job
            submit_endpoint = f"{self.BASE_URL}/transcript"
            response = await client.post(submit_endpoint, json=payload, headers=self._headers, timeout=30.0)
            response.raise_for_status()
            transcript_id = response.json()['id']
            print(f"STT job submitted with ID: {transcript_id}")

            # 4. Poll for the result
            api_result = await self._poll_for_result(client, transcript_id)
            print("STT job complete.")

            # 5. Transform and return the generic result
            return self._transform_to_generic_result(api_result)