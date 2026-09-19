"""
Tests for app.services.simple_mode_parser - the "magic" file parser that
auto-detects question/answer columns and tolerates malformed rows
(Simple Mode wizard, screen 5).

Covers: multilingual column detection (EN/UZ/RU headers), the
two-column fallback, the "give up gracefully -> unstructured" path for
files with no recognizable Q&A shape, blank-cell handling, malformed-CSV
resilience, and the JSON/JSONL shapes.

Uses real temp files (the parser reads from disk) but no DB or network.
"""

import json
import os
import tempfile

import pytest

from app.services.simple_mode_parser import parse_uploaded_file


def _write(tmp_path, name, content, mode="w"):
    p = os.path.join(tmp_path, name)
    with open(p, mode, encoding="utf-8" if "b" not in mode else None) as f:
        f.write(content)
    return p


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestColumnDetection:
    def test_english_headers(self, tmp_dir):
        p = _write(tmp_dir, "qa.csv", "question,answer\nHow?,Like this.\nWhy?,Because.\n")
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 2
        assert r.qa_pairs[0].question == "How?"
        assert r.qa_pairs[0].answer == "Like this."
        assert not r.has_unstructured_text

    def test_uzbek_headers(self, tmp_dir):
        p = _write(tmp_dir, "qa.csv", "savol,javob\nQanday?,Mana shunday.\n")
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 1
        assert r.qa_pairs[0].question == "Qanday?"

    def test_russian_headers_still_detected(self, tmp_dir):
        # The multilingual detector intentionally recognizes Russian
        # headers too (input handling, not UI language).
        p = _write(tmp_dir, "qa.csv", "вопрос,ответ\nКак?,Вот так.\n")
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 1

    def test_two_column_fallback_no_recognizable_headers(self, tmp_dir):
        # Exactly two columns, generic names -> assume (question, answer).
        p = _write(tmp_dir, "qa.csv", "col1,col2\nfoo,bar\nbaz,qux\n")
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 2
        assert r.qa_pairs[0].question == "foo"
        assert r.qa_pairs[0].answer == "bar"

    def test_many_columns_no_qa_becomes_unstructured(self, tmp_dir):
        # >2 columns and nothing recognizable -> don't guess, treat as
        # unstructured (safe fallback, not an error).
        p = _write(tmp_dir, "d.csv", "a,b,c,d\n1,2,3,4\n5,6,7,8\n")
        r = parse_uploaded_file(p, "csv")
        assert r.qa_pairs == []
        assert r.has_unstructured_text


class TestRowHandling:
    def test_blank_cells_counted_as_errors(self, tmp_dir):
        # Rows with an empty question or answer are skipped and counted.
        p = _write(
            tmp_dir, "qa.csv",
            "question,answer\nGood?,Yes.\n,Orphan answer\nOrphan question,\n",
        )
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 1
        assert r.error_row_count == 2

    def test_malformed_csv_recovers(self, tmp_dir):
        # An unescaped delimiter creates a row with too many fields. The
        # parser must skip the bad row, not fail the whole upload.
        content = "question,answer\nOk?,Fine.\nBad?,has,extra,commas\nAlso ok?,Sure.\n"
        p = _write(tmp_dir, "bad.csv", content)
        r = parse_uploaded_file(p, "csv")
        # The two well-formed rows survive; the bad one is counted.
        assert len(r.qa_pairs) == 2
        assert r.error_row_count >= 1

    def test_quoted_commas_are_not_errors(self, tmp_dir):
        # Properly quoted fields containing commas parse cleanly.
        content = 'question,answer\n"Price?","It is 10,000 UZS, roughly."\n'
        p = _write(tmp_dir, "q.csv", content)
        r = parse_uploaded_file(p, "csv")
        assert len(r.qa_pairs) == 1
        assert "10,000" in r.qa_pairs[0].answer


class TestJSON:
    def test_json_list_of_objects(self, tmp_dir):
        data = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        p = _write(tmp_dir, "d.json", json.dumps(data))
        r = parse_uploaded_file(p, "json")
        assert len(r.qa_pairs) == 2

    def test_json_wrapped_in_key(self, tmp_dir):
        data = {"data": [{"question": "Q", "answer": "A"}]}
        p = _write(tmp_dir, "d.json", json.dumps(data))
        r = parse_uploaded_file(p, "json")
        assert len(r.qa_pairs) == 1

    def test_jsonl(self, tmp_dir):
        lines = "\n".join(
            json.dumps(x) for x in [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        )
        p = _write(tmp_dir, "d.jsonl", lines)
        r = parse_uploaded_file(p, "jsonl")
        assert len(r.qa_pairs) == 2


class TestUnsupported:
    def test_unsupported_extension_raises(self, tmp_dir):
        p = _write(tmp_dir, "x.xyz", "whatever")
        with pytest.raises(ValueError):
            parse_uploaded_file(p, "xyz")
