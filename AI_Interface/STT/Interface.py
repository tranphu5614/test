from abc import ABC, abstractmethod
from dataclasses import dataclass,field
from typing import List
import os

# --- The Generic Data Models ---

@dataclass
class Word:
    """Represent a single transcirbed word with its timming"""
    text: str
    start: float
    end: float

@dataclass
class Utterance:
    """Represent a segment of speech from a single speaker"""
    speaker: str
    start: float
    end: float
    text: str
    words: List[Word] = field(default_factory=list)

@dataclass
class TranscriptionResult:
    """Represent the provider-agnostic result of transciption"""
    full_text: str
    utterances: List[Utterance] = field(default_factory=list)


# --- The Abstract Base Class of STT ---
class SpeechToTextInterface(ABC):
    """The Contract that all STT provider clients must follow"""
    @abstractmethod
    def transcribe(self, audio_source: str, enable_speaker_diarization: bool = False, language: str = None) -> TranscriptionResult:
        """
        Transribes an audio source

        Args:
            audio_source: Path to a local file or a public URL.
            enable_speaker_diarization: Whether to separate speakers.
            language: Optional language code (e.g.,'en_us').
        :param audio_source:
        :return:
            A TranscriptionResult object.
        """
        pass