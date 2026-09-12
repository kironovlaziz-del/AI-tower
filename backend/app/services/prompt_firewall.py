"""
Prompt Firewall

Runs on every AI request before it reaches the Policy Engine / provider call.
Two independent concerns, matching the architecture doc:

  - masking:        replace detected sensitive spans with a labelled
                     placeholder, e.g. "[MASKED:EMAIL]". The masked text is
                     what gets stored as `masked_input_text` and is what a
                     provider call would actually be sent (never the raw
                     input_text, which is retained only for audit/incident
                     investigation).
  - blocked fields:  a policy version can declare `blocked_terms`, a list of
                     case-insensitive substrings/phrases. If any is present
                     in the prompt, the request is rejected outright with
                     status "blocked" and is never sent anywhere.

This module has no DB dependency - it is pure text-in / result-out, so it's
easy to unit test and easy to extend with new detectors later (e.g. a
model-based PII detector) without touching the request service.
"""

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Pattern, Tuple


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
    # requirement, ISO dates like "2026-01-15" (10 chars with hyphens)
    # match the generic "digits with separators" pattern and get masked.
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+\d[\d\-\s()]{7,}\d|\(\d{2,4}\)[\d\-\s()]{5,}\d)(?!\d)"
        ),
    ),
]


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

    masked_text, flags = _mask_with_detectors(text)
    return FirewallResult(masked_text=masked_text, flags=flags, blocked=False)
