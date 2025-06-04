"""Speech to text utilities."""

from pathlib import Path
from typing import Any

import toml
import whisper
from pyannote.audio import Pipeline
from pyannote.core import Annotation
from pydantic import BaseModel, Field, field_validator
from textblob import TextBlob

from Backend.pyannote_utils import diarize_text

CONFIG_PATH = Path("config.toml")
CONFIG = toml.load(CONFIG_PATH)

class DiarizationSegment(BaseModel):
    """Validate Segment."""

    start: float = Field(..., ge=0, description="Start time of the speech segment")
    end: float = Field(..., gt=0, description="End time of the speech segment")
    speaker: str = Field(..., min_length=1, description="Speaker label")
    text: str = Field(..., min_length=1, description="Transcribed text")


class AudioFile(BaseModel):
    """Validate JSON object."""

    path: str

    @field_validator("path")
    @classmethod
    def check_file_exists(cls, value: str) -> str:
        """Check file if exists."""
        if not Path(value).is_file():
            err_code=f"File does not exist {value}"
            raise ValueError(err_code)
        return value


def speaker_diarize(file: str) -> Annotation:
    """Perform speaker diarization on the given audio file.

    Args:
        file (str): Path to the audio file.

    Returns:
        Any: The diarization result containing speaker segmentation.

    """
    use_auth_token = CONFIG["pyannote"]["use_auth_token"]
    validated_file = AudioFile(path=file)
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=use_auth_token,
    )
    return pipeline(validated_file.path)


def load_and_transcribe(file: str) -> list[tuple[Any, str, str]]:
    """Transcribes the given audio file using Whisper ASR and performs speaker diarization.

    Args:
        file (str): Path to the audio file.

    Returns:
        list[tuple[Any, str, str]]: A list of tuples containing segment details,
                                    speaker label, and transcribed text.

    """
    validated_file = AudioFile(path=file)
    model = whisper.load_model("turbo")
    asr_result = model.transcribe(validated_file.path)
    diarization_result = speaker_diarize(validated_file.path)
    final_result = diarize_text(asr_result, diarization_result)
    return [
        DiarizationSegment(start=seg.start, end=seg.end, speaker=spk, text=text)
        for seg, spk, text in final_result
    ]

def get_sentiment(sent: str = Field(..., min_length=1)) -> str:
    """Analyzes the sentiment of a given text.

    Args:
        sent (str): The input text.

    Returns:
        str: The sentiment label ('positive', 'negative', or 'neutral').

    """
    blob = TextBlob(sent)
    polarity: float = blob.sentiment.polarity
    sentiment: str = (
        "positive" if polarity > 0 else "negative" if polarity < 0 else "neutral"
    )
    return sentiment


def save_in_txt(result: list[DiarizationSegment]) -> list[str]:
    """Format the diarized and transcribed text with sentiment analysis.

    Args:
        result (list[DiarizationSegment]): A list of DiarizationSegment objects.

    Returns:
        list[str]: A list of formatted transcript lines with timestamps, speaker labels,
                   transcribed text, and sentiment analysis.

    """
    script_lines: list[str] = []
    for segment in result:
        line: str = f"{segment.start:.2f} {segment.end:.2f} {segment.speaker} {segment.text}"
        sentiment: str = get_sentiment(segment.text)
        line = f"{line} SENTIMENT:{sentiment}"
        script_lines.append(line)
    return script_lines
