"""
Prompt Firewall

Runs on every AI request before it reaches the Policy Engine / provider call.

Four layers of protection:

  1. Regex detectors - emails, credit cards, SSNs, IP addresses, API keys,
     phone numbers. Always on, zero dependencies.

  2. Blocked terms - the active policy version can declare a list of
     substrings that cause the entire prompt to be rejected.

  3. NER - person names, organizations, and locations via a spaCy model.
     Optional: when spacy or the model is missing, the layer is skipped.

  4. Gazetteer - fixed lists of well-known Uzbek cities and companies.
     Complements NER, which needs enough context to extract. A short
     prompt like "Aziz Karimov Toshkentga jonadi" may fall outside the
     training distribution, but the gazetteer always catches "Toshkent".

Regex, gazetteer, and NER run on the ORIGINAL text. Their matches are
merged by character offset with priority regex > gazetteer > NER: any
lower-priority match that overlaps a higher-priority one is dropped.
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


_DETECTORS: List[Tuple[str, Pattern[str]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "API_KEY",
        re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{12,}\b", re.IGNORECASE),
    ),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+\d[\d\-\s()]{7,}\d|\(\d{2,4}\)[\d\-\s()]{5,}\d)(?!\d)"
        ),
    ),
]


_NER_LABEL_MAP = {
    "PERSON": "PERSON",
    "PER": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "FAC": "LOCATION",
}


# ---------------------------------------------------------------------------
# Gazetteer for Uzbek entities
# ---------------------------------------------------------------------------
#
# Fixed lists of common entity mentions, applied only to uz by default.
# They are intentionally short and easy to extend - add entries as you
# collect more data. Each entry may be followed by a case suffix
# ("Toshkent" -> "Toshkentga", "Toshkentda", ...); the pattern consumes
# the suffix so the full token is masked.

_UZ_LOCATIONS = [
    "Toshkent", "Samarqand", "Buxoro", "Andijon", "Namangan", "Farg'ona",
    "Nukus", "Xiva", "Qarshi", "Termiz", "Chirchiq", "Angren",
    "Margilon", "Navoiy", "Jizzax", "Guliston", "Urganch", "Denov",
    "Kokand",
]
_UZ_LOCATION_SUFFIXES = ["ning", "ga", "da", "dan", "gacha", "dagi"]

_UZ_ORGS = [
    "UzAuto Motors", "Uztelecom", "Tashkent City", "Uzum Market",
    "Payme", "Click", "Humans", "UzCard", "Beeline Uzbekistan", "TBC Bank",
]


def _gazetteer_pattern(names: List[str], suffixes: List[str] | None = None) -> Pattern[str]:
    names_sorted = sorted(names, key=len, reverse=True)
    name_alt = "|".join(re.escape(n) for n in names_sorted)
    if suffixes:
        suf_alt = "|".join(re.escape(s) for s in suffixes)
        return re.compile(rf"\b(?:{name_alt})(?:{suf_alt})?\b")
    return re.compile(rf"\b(?:{name_alt})\b")


_GAZETTEER: dict = {
    "uz": [
        ("LOCATION", _gazetteer_pattern(_UZ_LOCATIONS, _UZ_LOCATION_SUFFIXES)),
        ("ORG", _gazetteer_pattern(_UZ_ORGS)),
    ],
}


def _gazetteer_matches(text: str, language: str) -> List[Tuple[int, int, str]]:
    out: List[Tuple[int, int, str]] = []
    for label, pattern in _GAZETTEER.get(language, []):
        for m in pattern.finditer(text):
            out.append((m.start(), m.end(), label))
    return out


# ---------------------------------------------------------------------------
# NER
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _load_ner(language: str):
    if not settings.PROMPT_FIREWALL_NER_ENABLED:
        return None

    models = settings.PROMPT_FIREWALL_NER_MODELS or {}
    model_path = models.get(language)
    if not model_path and settings.PROMPT_FIREWALL_NER_DEFAULT_LANG:
        model_path = models.get(settings.PROMPT_FIREWALL_NER_DEFAULT_LANG)
    if not model_path:
        return None

    try:
        import spacy  # type: ignore
    except ImportError:
        logger.warning(
            "PROMPT_FIREWALL_NER_ENABLED=true but spacy is not installed."
        )
        return None

    from pathlib import Path

    candidate = Path(model_path)
    if not candidate.is_absolute() and candidate.exists():
        resolved = str(candidate.resolve())
    else:
        resolved = model_path

    try:
        return spacy.load(resolved)
    except OSError:
        logger.warning(
            "spaCy model '%s' (language=%s) is not installed or not built yet.",
            model_path,
            language,
        )
        return None


def _ner_matches(text: str, language: str) -> List[Tuple[int, int, str]]:
    nlp = _load_ner(language)
    if nlp is None:
        return []
    doc = nlp(text)
    out: List[Tuple[int, int, str]] = []
    for ent in doc.ents:
        tag = _NER_LABEL_MAP.get(ent.label_)
        if tag:
            out.append((ent.start_char, ent.end_char, tag))
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _regex_matches(text: str) -> List[Tuple[int, int, str]]:
    out: List[Tuple[int, int, str]] = []
    for label, pattern in _DETECTORS:
        for m in pattern.finditer(text):
            out.append((m.start(), m.end(), label))
    return out


def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    a_s, a_e = a
    b_s, b_e = b
    return not (a_e <= b_s or a_s >= b_e)


def _find_blocked_terms(text: str, blocked_terms: Iterable[str]) -> List[str]:
    lowered = text.lower()
    hits = []
    for term in blocked_terms:
        term = (term or "").strip()
        if term and term.lower() in lowered:
            hits.append(term)
    return hits


def _apply_masks(text: str, matches: List[Tuple[int, int, str]]) -> str:
    if not matches:
        return text
    matches = sorted(matches, key=lambda x: x[0], reverse=True)
    result = text
    for start, end, label in matches:
        result = result[:start] + f"[MASKED:{label}]" + result[end:]
    return result


def _accept_by_priority(
    candidates: List[Tuple[int, int, str]],
    accepted: List[Tuple[int, int, str]],
) -> None:
    """
    Append candidates whose span does not overlap any already-accepted
    match. Accepts in the given order, so callers control priority by
    the order they invoke this function.
    """
    accepted_spans = [(s, e) for s, e, _ in accepted]
    for s, e, tag in candidates:
        if any(_overlaps((s, e), sp) for sp in accepted_spans):
            continue
        accepted.append((s, e, tag))
        accepted_spans.append((s, e))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan(
    text: str,
    blocked_terms: Iterable[str] | None = None,
    language: str = "en",
) -> FirewallResult:
    """
    Run the full firewall pipeline over a prompt.

    Priority order for overlapping spans: regex > gazetteer > NER.
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

    accepted: List[Tuple[int, int, str]] = []

    _accept_by_priority(_regex_matches(text), accepted)
    _accept_by_priority(_gazetteer_matches(text, language), accepted)
    _accept_by_priority(_ner_matches(text, language), accepted)

    flags: List[str] = []
    for _, _, label in accepted:
        f = f"masked:{label.lower()}"
        if f not in flags:
            flags.append(f)

    masked_text = _apply_masks(text, accepted)

    return FirewallResult(masked_text=masked_text, flags=flags, blocked=False)
