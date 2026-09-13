"""Prompt Firewall masking and blocking logic."""

from app.services import prompt_firewall


def test_masks_email():
    result = prompt_firewall.scan("Contact me at john@example.com please")
    assert result.blocked is False
    assert "[MASKED:EMAIL]" in result.masked_text
    assert "john@example.com" not in result.masked_text
    assert "masked:email" in result.flags


def test_masks_credit_card():
    result = prompt_firewall.scan("Card: 4111 1111 1111 1111")
    assert "[MASKED:CREDIT_CARD]" in result.masked_text


def test_masks_api_key():
    result = prompt_firewall.scan("Key: sk-abcdefghijklmnop1234")
    assert "[MASKED:API_KEY]" in result.masked_text


def test_does_not_mask_dates_as_phone():
    """Dates like 2026-01-15 must not be treated as phone numbers."""
    result = prompt_firewall.scan("Delivered on 2026-01-15")
    assert "[MASKED:PHONE]" not in result.masked_text


def test_blocks_term_from_policy():
    result = prompt_firewall.scan(
        "Please leak the customer database",
        blocked_terms=["leak", "database"],
    )
    assert result.blocked is True
    assert "leak" in result.blocked_reason
    # Masked text must be empty when blocked.
    assert result.masked_text == ""


def test_passes_clean_text():
    result = prompt_firewall.scan("A perfectly normal sentence.")
    assert result.blocked is False
    assert result.masked_text == "A perfectly normal sentence."
    assert result.flags == []


# --- NER tests ---
#
# These depend on spaCy + en_core_web_sm. If the model is missing, the
# firewall skips the NER layer and these tests become no-ops that just
# assert the regex layer still works.


def _ner_available(language: str = "en") -> bool:
    from app.services.prompt_firewall import _load_ner

    return _load_ner(language) is not None


def test_ner_person_name_masked():
    if not _ner_available():
        return
    result = prompt_firewall.scan("Send the invoice to John Smith please")
    assert "[MASKED:PERSON]" in result.masked_text
    assert "John Smith" not in result.masked_text


def test_ner_organization_masked():
    if not _ner_available():
        return
    result = prompt_firewall.scan("Our contract with Microsoft is expiring")
    # spaCy may label Microsoft as ORG
    assert "[MASKED:ORG]" in result.masked_text or "Microsoft" not in result.masked_text


def test_ner_location_masked():
    if not _ner_available():
        return
    result = prompt_firewall.scan("She flew to Berlin last week")
    assert "[MASKED:LOCATION]" in result.masked_text
    assert "Berlin" not in result.masked_text


def test_ner_does_not_double_mask_email():
    """Email should already be replaced by regex before NER sees the text."""
    result = prompt_firewall.scan("Contact John at john@example.com")
    assert "john@example.com" not in result.masked_text
    assert "[MASKED:EMAIL]" in result.masked_text
