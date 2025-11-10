LLM_TASKS = {
    "summarization": {
        "description": "Generate a concise, neutral paragraph summarizing the key points and outcome of the conversation.",
        "output_schema": """
        A JSON object with a single key "summary".
        The value of "summary" should be a string containing the summary text.
        Example: {"summary": "The customer called to report a billing issue and the agent resolved it by applying a credit."} 
        """
    },

    "sentiment_analysis": {
        "description": "Analyze the sentiment of EACH utterance in the transcript.",
        "output_schema": """
        A JSON object with a single key "utterance_sentiments".
        The value of "utterance_sentiments" must be a list of JSON objects.
        Each object in the list must have exactly these three keys:
        1. "utterance_index": The integer index of the utterance from the provided transcript (e.g., 0, 1, 2).
        2. "sentiment": A single string value, which must be one of ["POSITIVE", "NEGATIVE", "NEUTRAL"].
        3. "score": A float value from -1.0 (most negative) to 1.0 (most positive), representing the intensity of the sentiment.
        Example: {"utterance_sentiments": [{"utterance_index": 0, "sentiment": "NEUTRAL", "score":0.1},...]}
        """
    },

    "action_item_extraction": {
        "description": "Extract all explicit action items, follow-up tasks, or commitments made during the conversation.",
        "output_schema": """
        A JSON object with a single key "action_items".
        The value of "action_items" must be a list of JSON objects.
        Each object in the list must have exactly these three keys:
        - "task": A clear, concise string describing the action to be taken.
        - "owner": A string identifying who is responsible for the action (e.g., "Support Agent", "Customer", "System").
        - "context": The original string from the transcript that implies the action.
        If no action items are found, the list should be empty.
        Example: {"action_items": [{"task": "Send a confirmation email to the customer", "owner": "Support Agent", "context": "Okay, I will send you that confirmation email right away."}]}
        """
    },

    "call_categorization": {
        "description": "Categorize the primary purpose of the call into one of the following predefined categories: 'Sales Inquiry', 'Technical Support', 'Billing Issue', 'Account Management', or 'General Question'.",
        "output_schema": """
        A JSON object with a single key "category".
        The value of "category" must be string that is one of the predefined categories.
        Example: {"category": "Billing Issue"}
        """
    }
}