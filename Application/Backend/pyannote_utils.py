"""Pyannote Utility."""

from typing import Any

from pyannote.core import Annotation, Segment
from pydantic import BaseModel, Field, ValidationInfo, field_validator


class TranscriptionSegment(BaseModel):
    """Represent a segment of transcribed text with timestamps."""

    start: float = Field(..., ge=0, description="Start time of the speech segment")
    end: float = Field(..., gt=0, description="End time of the speech segment")
    text: str = Field(..., min_length=1, description="Transcribed text")

    @field_validator("start", "end")
    @classmethod
    def validate_timestamps(cls, value: float, values: ValidationInfo) -> float:
        """Ensure that timestamps are non-negative and end is greater than start."""
        if value < 0:
            err_code="Timestamps must be non-negative."
            raise ValueError(err_code)
        start = values.data.get("start")
        end = values.data.get("end")
        if start is not None and end is not None and end <= start:
            err_code="End time must be greater than start time."
            raise ValueError(err_code)
        return value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Ensure that text is non-empty or whitespace-only."""
        if not value.strip():
            err_code="Text cannot be empty or whitespace."
            raise ValueError(err_code)
        return value

class TranscriptionResult(BaseModel):
    """Represent the complete transcription result containing multiple segments."""

    segments: list[TranscriptionSegment]

def get_text_with_timestamp(transcribe_res: dict[str, Any]) -> list[tuple[Segment, str]]:
    """Extract text segments with their corresponding timestamps from transcription results."""
    validated_transcribe_res = TranscriptionResult(**transcribe_res)
    return [(Segment(item.start, item.end), item.text) for item in validated_transcribe_res.segments]

def add_speaker_info_to_text(timestamp_texts: list[tuple[Segment, str]], ann: Annotation) -> list[tuple[Segment, str, str]]:
    """Add speaker information to each text segment based on diarization results."""
    spk_text: list[tuple[Segment, str, str]] = []
    for seg, text in timestamp_texts:
        spk: str = ann.crop(seg).argmax()
        spk_text.append((seg, spk, text))
    return spk_text

def merge_data(text_data: list[tuple[Segment, str, str]]) -> tuple[Segment, str, str]:
    """Merge multiple text segments from the same speaker into a single consolidated segment."""
    sentence: str = "".join([item[-1] for item in text_data])
    spk: str = text_data[0][1]
    start: float = text_data[0][0].start
    end: float = text_data[-1][0].end
    return Segment(start, end), spk, sentence

# Punctuation marks that typically indicate the end of a sentence
PUNC_SENT_END: list[str] = [".", "?", "!"]

def merge_sentence(spk_text: list[tuple[Segment, str, str]]) -> list[tuple[Segment, str, str]]:
    """Merge text segments into coherent sentences based on speaker changes and sentence-ending punctuation."""
    merged_spk_text: list[tuple[Segment, str, str]] = []
    pre_spk: str = None
    text_data: list[tuple[Segment, str, str]] = []

    for seg, spk, text in spk_text:
        if spk != pre_spk and pre_spk is not None and len(text_data) > 0:
            merged_spk_text.append(merge_data(text_data))
            text_data = [(seg, spk, text)]
            pre_spk = spk

        elif text and len(text) > 0 and text[-1] in PUNC_SENT_END:
            text_data.append((seg, spk, text))
            merged_spk_text.append(merge_data(text_data))
            text_data = []
            pre_spk = spk
        else:
            text_data.append((seg, spk, text))
            pre_spk = spk

    if len(text_data) > 0:
        merged_spk_text.append(merge_data(text_data))

    return merged_spk_text

def diarize_text(transcribe_res: dict[str, Any], diarization_result: Annotation) -> list[tuple[Segment, str, str]]:
    """Perform full text diarization by combining transcription and speaker diarization results."""
    timestamp_texts = get_text_with_timestamp(transcribe_res)
    spk_text = add_speaker_info_to_text(timestamp_texts, diarization_result)
    return merge_sentence(spk_text)
