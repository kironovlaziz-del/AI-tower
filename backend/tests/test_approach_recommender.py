"""
Tests for app.services.approach_recommender - the RAG vs fine-tuning
decision heuristic used by Simple Mode (wizard screen 6).

These lock in the decision table so a future change to the thresholds or
branches can't silently alter which approach the wizard picks. Pure
function, no DB, no mocks.
"""

import pytest

from app.services.approach_recommender import (
    recommend_approach,
    FEW_SHOT_THRESHOLD,
)


class TestClassification:
    def test_classification_always_fine_tuning_classifier(self):
        # A classification task is a classifier-training job regardless of
        # data shape.
        r = recommend_approach("classification", has_documents=True, qa_pair_count=1000)
        assert r.approach == "fine_tuning_classification"
        r2 = recommend_approach("classification", has_documents=False, qa_pair_count=0)
        assert r2.approach == "fine_tuning_classification"


class TestStyleWriting:
    def test_style_writing_is_fine_tuning(self):
        # "Write in our style" is the canonical fine-tuning signal.
        r = recommend_approach("style_writing", has_documents=False, qa_pair_count=200)
        assert r.approach == "fine_tuning"

    def test_style_writing_even_with_documents(self):
        # Style intent wins over having documents.
        r = recommend_approach("style_writing", has_documents=True, qa_pair_count=0)
        assert r.approach == "fine_tuning"


class TestSupportQA:
    def test_documents_only_is_rag(self):
        r = recommend_approach("support_qa", has_documents=True, qa_pair_count=0)
        assert r.approach == "rag"

    def test_few_pairs_is_rag_few_shot(self):
        # Below the threshold -> RAG with few-shot examples.
        r = recommend_approach("support_qa", has_documents=False, qa_pair_count=10)
        assert r.approach == "rag_few_shot"

    def test_just_below_threshold_is_few_shot(self):
        r = recommend_approach(
            "support_qa", has_documents=False, qa_pair_count=FEW_SHOT_THRESHOLD - 1
        )
        assert r.approach == "rag_few_shot"

    def test_at_threshold_is_rag(self):
        # At or above the threshold -> plain RAG (facts task stays RAG).
        r = recommend_approach(
            "support_qa", has_documents=False, qa_pair_count=FEW_SHOT_THRESHOLD
        )
        assert r.approach == "rag"

    def test_many_pairs_is_rag(self):
        r = recommend_approach("support_qa", has_documents=False, qa_pair_count=5000)
        assert r.approach == "rag"

    def test_no_data_at_all_is_rag(self):
        # Nothing yet -> start with an empty RAG knowledge base.
        r = recommend_approach("support_qa", has_documents=False, qa_pair_count=0)
        assert r.approach == "rag"


class TestOtherTaskType:
    def test_other_behaves_like_support_qa(self):
        # "other" falls into the facts/RAG branch, same thresholds.
        assert recommend_approach("other", True, 0).approach == "rag"
        assert recommend_approach("other", False, 5).approach == "rag_few_shot"
        assert recommend_approach("other", False, 100).approach == "rag"


class TestReasonText:
    def test_every_result_has_nonempty_reason(self):
        # The wizard shows `reason` to the user; it must never be empty.
        for task in ("classification", "style_writing", "support_qa", "other"):
            for docs in (True, False):
                for n in (0, 10, 100):
                    r = recommend_approach(task, docs, n)
                    assert r.reason and r.reason.strip()

    def test_reason_is_ascii_english(self):
        # Project is English/Uzbek only - reasons must not contain Cyrillic.
        import re

        for task in ("classification", "style_writing", "support_qa", "other"):
            for docs in (True, False):
                for n in (0, 10, 100):
                    r = recommend_approach(task, docs, n)
                    assert not re.search("[а-яА-Я]", r.reason), (
                        f"Cyrillic in reason for {task}/{docs}/{n}: {r.reason}"
                    )
