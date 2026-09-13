"""Uzbek NER tests. Skip when the uz_ner_model is not built yet."""

from pathlib import Path

import pytest

from app.services import prompt_firewall

MODEL_DIR = (
    Path(__file__).resolve().parents[1]
    / "ner_training"
    / "output"
    / "uz_ner_model"
)


def _uz_available() -> bool:
    return MODEL_DIR.exists()


@pytest.mark.skipif(not _uz_available(), reason="uz_ner_model not built")
def test_uz_masks_person_name():
    result = prompt_firewall.scan(
        "Aziz Karimov Toshkentga jonadi", language="uz"
    )
    assert "[MASKED:PERSON]" in result.masked_text
    assert "Aziz Karimov" not in result.masked_text


@pytest.mark.skipif(not _uz_available(), reason="uz_ner_model not built")
def test_uz_masks_location():
    result = prompt_firewall.scan(
        "Uzum Market Samarqandda yangi ofis ochdi", language="uz"
    )
    assert (
        "[MASKED:ORG]" in result.masked_text
        or "[MASKED:LOCATION]" in result.masked_text
    )


@pytest.mark.skipif(not _uz_available(), reason="uz_ner_model not built")
def test_uz_email_still_masked_by_regex():
    """Regex layer runs before NER, regardless of language."""
    result = prompt_firewall.scan(
        "Aloqa uchun: john@example.com", language="uz"
    )
    assert "[MASKED:EMAIL]" in result.masked_text


@pytest.mark.skipif(not _uz_available(), reason="uz_ner_model not built")
def test_uz_clean_text_unchanged():
    result = prompt_firewall.scan(
        "Bugun havo juda issiq", language="uz"
    )
    assert result.masked_text == "Bugun havo juda issiq"
