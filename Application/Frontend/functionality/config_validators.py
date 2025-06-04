"""Validate the words_config.yaml file using Pydantic."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.traceback import install

install()
console = Console()


class PersonalInformationPatterns(BaseModel):
    """Regex patterns for personal information detection."""

    phone_number: str = r"\d{4}-\d{4}"
    date_dd_mm_yyyy: str = r"\d{2}-\d{2}-\d{4}"
    multi_4_digit_patt: str = r"\b\d{4}\b.*\b\d{4}\b"


class SensitiveInformationPatterns(BaseModel):
    """Regex patterns for sensitive information detection."""

    credit_card: str = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
    atm_pin: str = r"\b\d{4}\b"
    account_password: str = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$" # noqa: S105


class WordsConfigSchema(BaseModel):
    """Schema for validating words_config.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    Greetings: list[str]
    Disclaimers: list[str]
    ProhibitedPhrases: list[str]
    ClosingStatements: list[str]
    PersonalInformationPatterns: PersonalInformationPatterns
    SensitiveInformationPatterns: SensitiveInformationPatterns


def validate_words_config(file_name: str) -> WordsConfigSchema | None:
    """Validate the words_config.yaml file using Pydantic.

    Returns: WordsConfigSchema | None: Validated schema or None if validation fails.
    """
    try:
        with Path(file_name).open(encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        config = WordsConfigSchema(**yaml_data)

    except (yaml.YAMLError, ValueError):
        return None
    else:
        return config
