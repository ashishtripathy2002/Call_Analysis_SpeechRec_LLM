"""Parse the text transcript into a json object."""

from functionality.validators_detectors import (
    detect_personal_details,
    detect_prohibited_phrases,
    required_phrase_validation,
)
from pydantic import BaseModel, Field


class ConversationFormat(BaseModel):
    """Check format for the conversation_json generated."""

    start_time: float = Field(
        ...,
        ge=0,
        description="Dialog start time for the speaker",
    )
    end_time: float = Field(
        ...,
        ge=0,
        description="Dialog end time for the speaker",
    )
    speaker: str = Field(
        ...,
        description="Identify if it is client or handler speaking",
    )
    text: str = Field(
        ...,
        description="Speaker's dialog",
    )
    sentiment: str = Field(
        ...,
        description="Sentiment of the dialog (positive, neutral or negative)",
    )
    req_phrase_cat: list[str] = Field(
        ...,
        description="List of required phrases categories in dialog. Eg greeting or disclaimer",
    )
    pil_category: list[str] = Field(
        ...,
        description="List of detected personal identifiable information leaks",
    )
    prohibited_words: list[str] = Field(
        ...,
        description="List of prohibited words detected in the dialog",
    )


class AttrbFormat(BaseModel):
    """Check format for the attr_params generated."""

    total_agent_time: float = Field(
        ...,
        ge=0,
        description="Total time the agent spoke",
    )
    total_customer_time: float = Field(
        ...,
        ge=0,
        description="Total time the customer spoke",
    )
    total_agent_words: int = Field(
        ...,
        ge=0,
        description="Total number of words spoken by the agent",
    )
    total_customers_words: int = Field(
        ...,
        ge=0,
        description="Total number of words spoken by the customer",
    )
    total_greetings: int = Field(
        ...,
        ge=0,
        description="Number of greetings detected in the transcript",
    )
    total_disclaimers: int = Field(
        ...,
        ge=0,
        description="Total number of disclaimers detected in the transcript",
    )
    total_closures: int = Field(
        ...,
        ge=0,
        description="Total number of  closures detected in the transcript",
    )
    total_pil: int = Field(
        ...,
        ge=0,
        description="Total number personal identifiable information (PII) mentions",
    )
    total_prohibited_words: int = Field(
        ...,
        ge=0,
        description="Total number of prohibited words used",
    )


class SentimentFormat(BaseModel):
    """Check format for the sentiment_counts generated."""

    speakers: dict[str, dict[str, int]] = Field(
        ...,
        description="Count of positive, neutral amd negative sentiments at an overall level and for each speaker",
    )


def text_to_json(text: str) -> tuple[list[ConversationFormat], AttrbFormat, SentimentFormat]:
    """Convert the text transcript to a json object.

    - Return the whole transcript.
    """
    lines = text.strip().split("\n")
    conversation = []
    total_greets, total_disclaims, total_closures, total_pil, total_prohibited_words = 0, 0, 0, 0, 0
    agent_time, customer_time, total_agent_words, total_customers_words = 0, 0, 0, 0
    sentiment_counts = {
        "speakers": {
            "Net": {"positive": 0, "neutral": 0, "negative": 0},
            "Handler": {"positive": 0, "neutral": 0, "negative": 0},
            "Client": {"positive": 0, "neutral": 0, "negative": 0},
        },
    }

    for line in lines:
        # Split each line into components
        parts = line.split(" ", 3)
        start_time = float(parts[0])
        end_time = float(parts[1])
        speaker = parts[2]
        # Remove sentiment from the text
        text = parts[3].rsplit(" SENTIMENT:", 1)[0]
        # store sentiment
        sentiment = parts[3].rsplit(" SENTIMENT:", 1)[1].strip()

        new_greets, new_disclaims, new_closures, req_phrase_cat = required_phrase_validation(text) if speaker == "SPEAKER_01" else (0, 0, 0, [])
        total_greets, total_disclaims, total_closures = total_greets + new_greets, total_disclaims + new_disclaims, total_closures + new_closures

        new_pil, pil_cat = detect_personal_details(text) if speaker == "SPEAKER_00" else (0, [])
        total_pil = total_pil + new_pil

        prohibited_words_count, prohibited_words = detect_prohibited_phrases(text)
        total_prohibited_words += prohibited_words_count

        agent_time += end_time - start_time if speaker == "SPEAKER_01" else 0
        customer_time += end_time - start_time if speaker == "SPEAKER_00" else 0

        total_agent_words += len(text.split()) if speaker == "SPEAKER_01" else 0
        total_customers_words += len(text.split()) if speaker == "SPEAKER_00" else 0

        # Net count of sentiments
        if sentiment in sentiment_counts["speakers"]["Net"]:
            sentiment_counts["speakers"]["Net"][sentiment] += 1
            if speaker == "SPEAKER_01":
                sentiment_counts["speakers"]["Handler"][sentiment] += 1
            elif speaker == "SPEAKER_00":
                sentiment_counts["speakers"]["Client"][sentiment] += 1

        # Append the parsed data as a dictionary
        conversation.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "speaker": speaker,
                "text": text,
                "sentiment": sentiment,
                "req_phrase_cat": req_phrase_cat,
                "pil_category": pil_cat,
                "prohibited_words": prohibited_words,
            },
        )

    attr_params = {
        "total_agent_time": agent_time,
        "total_customer_time": customer_time,
        "total_agent_words": total_agent_words,
        "total_customers_words": total_customers_words,
        "total_greetings": total_greets,
        "total_disclaimers": total_disclaims,
        "total_closures": total_closures,
        "total_pil": total_pil,
        "total_prohibited_words": total_prohibited_words,
    }

    return conversation, attr_params, sentiment_counts


