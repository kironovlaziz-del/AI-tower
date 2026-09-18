"""
Simple Mode wizard, screen 5 ("magic" parsing): given a file the person
just uploaded, figure out on its own whether it contains structured
question/answer pairs (for fine-tuning / RAG few-shot) or is just prose
text (for RAG) - the plan is explicit that the person should never be
asked to configure column mapping.

Column detection is intentionally simple and multilingual (Russian/
Uzbek/English keywords, since that's this product's actual audience),
with a conservative fallback: exactly two columns and neither name
matches a keyword -> assume (question, answer) in that order, since
that is by far the most common shape for a naive two-column export.
If a file has more than two columns and none of them look like a
question/answer pair, we deliberately do NOT guess further - it is
treated as unstructured text instead (has_documents=True in the
approach_recommender sense), which is the safe fallback: it still gives
the wizard a usable next step (RAG) instead of blocking the person with
a "we couldn't understand your file" dead end.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.services.rag_service import extract_text as rag_extract_text

STRUCTURED_EXTENSIONS = {"csv", "tsv", "xlsx", "json", "jsonl"}
UNSTRUCTURED_EXTENSIONS = {"txt", "pdf"}
SUPPORTED_EXTENSIONS = STRUCTURED_EXTENSIONS | UNSTRUCTURED_EXTENSIONS

QUESTION_EXACT = {"q", "question", "вопрос", "savol", "prompt", "input", "запрос"}
QUESTION_SUBSTRINGS = ("question", "вопрос", "savol")
ANSWER_EXACT = {"a", "answer", "ответ", "javob", "response", "output", "reply"}
ANSWER_SUBSTRINGS = ("answer", "ответ", "javob")


@dataclass
class QAPairResult:
    question: str
    answer: str


@dataclass
class ParseResult:
    qa_pairs: List[QAPairResult] = field(default_factory=list)
    error_row_count: int = 0
    has_unstructured_text: bool = False
    detected_columns: Optional[List[str]] = None
    preview_text: Optional[str] = None  # first ~500 chars, for unstructured files


def _classify_column(name: str) -> Optional[str]:
    normalized = str(name).strip().lower()
    if normalized in QUESTION_EXACT or any(s in normalized for s in QUESTION_SUBSTRINGS):
        return "question"
    if normalized in ANSWER_EXACT or any(s in normalized for s in ANSWER_SUBSTRINGS):
        return "answer"
    return None


def _dataframe_to_qa(df: pd.DataFrame) -> ParseResult:
    q_col = a_col = None
    for col in df.columns:
        role = _classify_column(col)
        if role == "question" and q_col is None:
            q_col = col
        elif role == "answer" and a_col is None:
            a_col = col

    if (q_col is None or a_col is None) and len(df.columns) == 2:
        # Conservative fallback for a plain two-column export with
        # generic header names (or no recognizable header at all).
        q_col, a_col = df.columns[0], df.columns[1]

    if q_col is None or a_col is None:
        # More than two columns and nothing recognizable - don't guess;
        # treat as unstructured so the wizard still has a safe next step.
        return ParseResult(has_unstructured_text=True, detected_columns=list(df.columns))

    pairs: List[QAPairResult] = []
    error_rows = 0
    for _, row in df.iterrows():
        q = row.get(q_col)
        a = row.get(a_col)
        q_str = "" if pd.isna(q) else str(q).strip()
        a_str = "" if pd.isna(a) else str(a).strip()
        if not q_str or not a_str:
            error_rows += 1
            continue
        pairs.append(QAPairResult(question=q_str, answer=a_str))

    return ParseResult(
        qa_pairs=pairs, error_row_count=error_rows, detected_columns=[q_col, a_col]
    )


def parse_uploaded_file(file_path: str, file_type: str) -> ParseResult:
    file_type = file_type.lower().lstrip(".")

    if file_type == "csv":
        return _read_delimited(file_path, sep=",")

    if file_type == "tsv":
        return _read_delimited(file_path, sep="\t")

    if file_type == "xlsx":
        df = pd.read_excel(file_path, dtype=str)
        return _dataframe_to_qa(df)

    if file_type in ("json", "jsonl"):
        records = _load_json_records(file_path, file_type)
        df = pd.DataFrame(records)
        return _dataframe_to_qa(df)

    if file_type in ("txt", "pdf"):
        text = rag_extract_text(file_path, file_type)
        return ParseResult(has_unstructured_text=True, preview_text=text[:500])

    raise ValueError(
        f"Unsupported file type '.{file_type}'. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def _read_delimited(file_path: str, sep: str) -> ParseResult:
    """
    Real-world exports are frequently malformed (an unescaped comma/tab
    inside a field is the single most common case) - the "magic" parsing
    step promises the person never has to think about file format, so a
    row-count mismatch must degrade to "skip that row" rather than a
    crash. pandas' default C parser raises ParserError on any row with
    the wrong number of fields; the python engine's on_bad_lines="skip"
    tolerates that, at the cost of being slower - an acceptable trade for
    files this small.
    """
    try:
        df = pd.read_csv(file_path, sep=sep, dtype=str, keep_default_na=True)
        return _dataframe_to_qa(df)
    except pd.errors.ParserError:
        bad_lines = []
        df = pd.read_csv(
            file_path,
            sep=sep,
            dtype=str,
            keep_default_na=True,
            engine="python",
            on_bad_lines=lambda line: bad_lines.append(line) or None,
        )
        result = _dataframe_to_qa(df)
        result.error_row_count += len(bad_lines)
        return result


def _load_json_records(file_path: str, file_type: str) -> List[dict]:
    if file_type == "jsonl":
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # A single {"question": ..., "answer": ...} object, or a wrapper
        # like {"data": [...]} / {"pairs": [...]} - try the common shapes
        # before giving up and treating the whole thing as one record.
        for key in ("data", "pairs", "items", "examples"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    raise ValueError("JSON file must contain a list of objects or a single object")
