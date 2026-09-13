"""
Prompt Firewall

Runs on every AI request before it reaches the Policy Engine / provider call.

Three layers of protection:

  1. Regex detectors - emails, credit cards, SSNs, IP addresses, API keys,
     phone numbers. Always on, zero dependencies.

  2. Blocked terms - the active policy version can declare a list of
     substrings that cause the entire prompt to be rejected.

  3. NER - person names, organizations, and locations are detected with a
     spaCy model. This is optional: when spacy or the configured model is
     not installed, the layer is skipped and a warning is raised once.

Masked text is what actually gets stored as `masked_input_text` and sent
to the provider. The raw input is only kept (encrypted) for audit.
"""

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, List, Pattern, Tuple

from app.core.config import settings

logger = logging.getLogger("prompt_firewall")


@dataclass
class FirewallResult:
    masked_text: str
    flags: List[str] = field(default_factory=list)
    blocked: bool = False
    blocked_reason: str | None = None


# label -> compiled regex. Order matters only in that overlapping matches
# from an earlier pattern are masked first, so put more specific patterns
# before more generic ones.
_DETECTORS: List[Tuple[str, Pattern[str]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "API_KEY",
        re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{12,}\b", re.IGNORECASE),
    ),
    # Phones must contain a "+" prefix or parentheses. Without that
    # requirement, ISO dates like "2026-01-15" match the generic
    # "digits with separators" pattern and get masked.
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+\d[\d\-\s()]{7,}\d|\(\d{2,4}\)[\d\-\s()]{5,}\d)(?!\d)"
        ),
    ),
]


# NER label -> mask tag. spaCy returns raw labels like "PERSON" or "GPE".
_NER_LABEL_MAP = {
    "PERSON": "PERSON",
    "PER": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
}


def _mask_with_detectors(text: str) -> Tuple[str, List[str]]:
    flags: List[str] = []
    result = text
    for label, pattern in _DETECTORS:
        def _replace(match: re.Match, label=label) -> str:
            return f"[MASKED:{label}]"

        new_result, count = pattern.subn(_replace, result)
        if count:
            flags.append(f"masked:{label.lower()}")
            result = new_result
    return result, flags


@lru_cache(maxsize=1)
def _load_ner():
    """
    Lazily load the spaCy NER model. Returns None when spacy or the
    configured model are not available; the caller treats None as
    "NER disabled" and continues with regex only.
    """
    if not settings.PROMPT_FIREWALL_NER_ENABLED:
        return None
    try:
        import spacy  # type: ignore
    except ImportError:
        logger.warning(
            "PROMPT_FIREWALL_NER_ENABLED=true but spacy is not installed. "
            "Install it with: pip install spacy && python -m spacy download %s",
            settings.PROMPT_FIREWALL_NER_MODEL,
        )
        return None
    try:
        return spacy.load(settings.PROMPT_FIREWALL_NER_MODEL)
    except OSError:
        logger.warning(
            "spaCy model '%s' is not installed. Run: python -m spacy download %s",
            settings.PROMPT_FIREWALL_NER_MODEL,
            settings.PROMPT_FIREWALL_NER_MODEL,
        )
        return None


def _mask_with_ner(text: str) -> Tuple[str, List[str]]:
    """
    Replace detected person names, organizations, and locations with
    labelled placeholders. Operates right-to-left so earlier character
    offsets stay valid after each substitution.
    """
    nlp = _load_ner()
    if nlp is None:
        return text, []

    flags: List[str] = []
    doc = nlp(text)

    replacements: List[Tuple[int, int, str, str]] = []
    for ent in doc.ents:
        tag = _NER_LABEL_MAP.get(ent.label_)
        if not tag:
            continue
        # Skip entities that are already inside a [MASKED:...] marker -
        # regex layer may have replaced the original text with one of our
        # placeholders that happens to look like a proper noun.
        if text[max(ent.start_char - 1, 0):ent.start_char] == ":":
            continue
        replacements.append((ent.start_char, ent.end_char, tag, ent.text))

    if not replacements:
        return text, []

    # Sort descending by start so we can rebuild the string without
    # invalidating offsets.
    replacements.sort(key=lambda x: x[0], reverse=True)
    result = text
    for start, end, tag, original in replacements:
        result = result[:start] + f"[MASKED:{tag}]" + result[end:]
        flags.append(f"masked:{tag.lower()}")

    return result, flags


def _find_blocked_terms(text: str, blocked_terms: Iterable[str]) -> List[str]:
    lowered = text.lower()
    hits = []
    for term in blocked_terms:
        term = (term or "").strip()
        if term and term.lower() in lowered:
            hits.append(term)
    return hits


def scan(text: str, blocked_terms: Iterable[str] | None = None) -> FirewallResult:
    """
    Run the full firewall pipeline over a prompt.

    blocked_terms comes from the org's active policy version
    (rules_json["blocked_terms"]), if any is linked to the use case.

    Pipeline order:
      1. Blocked terms (reject entire prompt if hit).
      2. Regex masking (emails, cards, phones, keys, ...).
      3. NER masking (persons, organizations, locations).
    """
    blocked_terms = list(blocked_terms or [])

    hits = _find_blocked_terms(text, blocked_terms)
    if hits:
        return FirewallResult(
            masked_text="",
            flags=[f"blocked_term:{h}" for h in hits],
            blocked=True,
            blocked_reason=f"Prompt contains a blocked term: {hits[0]}",
        )

    masked_text, regex_flags = _mask_with_detectors(text)
    masked_text, ner_flags = _mask_with_ner(masked_text)

    return FirewallResult(
        masked_text=masked_text,
        flags=regex_flags + ner_flags,
        blocked=False,
    )
