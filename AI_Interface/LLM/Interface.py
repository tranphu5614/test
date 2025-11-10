from abc import ABC, abstractmethod
from typing import Dict, Any
from AI_Interface.STT.Interface import TranscriptionResult

# The return type is a generic dictionary. This is the fundamental
# structure for key-value data, aligning with our principles.
GenericAnalysisResult = Dict[str, Any]

class LanguageModelInterface(ABC):
    """
    A generic, task-agnostic interface for performing text analysis with an LLM.
    This interface is stable and should not change even when new tasks are added.
    """
    @abstractmethod
    def analyze(self, transcript: TranscriptionResult, task_name: str) -> GenericAnalysisResult:
        """
        Performs a specified analysis task on a transcript.

        Args:
            transcript: The TranscriptionResult object.
            task_name: The key of the task to perform (e.g., 'summarization'),
                       which corresponds to an entry in the tasks.py registry.

        Returns:
            A dictionary containing the structured analysis result from the LLM.
        """
        pass