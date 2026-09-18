"""
Simple Mode: RAG vs Fine-tuning recommendation.

Translates the plan's decision table into a deterministic, explainable
function. The wizard never asks the person to choose between RAG and
fine-tuning directly (per the plan's design principle: "система сама
решает... пользователь просто нажимает Продолжить") - it infers the
right approach from two things it already knows by the time this
decision is made (wizard screen 6, right after data parsing):

1. What the model should do (task_type) - this is collected explicitly
   at wizard screen 2 ("Что должна делать модель?"), so "style_writing"
   IS the plan's "в фирменном стиле" signal. There's no need to try to
   detect writing style from raw text statistically - the person already
   told us via their screen-2 choice, and inferring it a second time from
   data would be both redundant and far less reliable.
2. What data shape they have: pure unstructured documents (has_documents)
   vs structured question/answer pairs (qa_pair_count).

Decision table (docs/plan reference):
    classification task                              -> fine_tuning_classification
    style_writing task                                -> fine_tuning
    facts/support task, only documents, no Q&A pairs  -> rag
    facts/support task, < 50 Q&A pairs                -> rag_few_shot
    facts/support task, >= 50 Q&A pairs (or + docs)   -> rag
    facts/support task, no data at all yet            -> rag (start empty, add docs later)

RAG stays the default for the facts/support branch even with a large
Q&A corpus: retrieval is cheaper, faster to update (no retraining when
an answer changes), and per the plan's own framing is "10x faster and
simpler" for tasks that are fundamentally "answer from known facts"
rather than "write in a specific voice".
"""

from dataclasses import dataclass
from typing import Literal

TaskType = Literal["support_qa", "style_writing", "classification", "other"]
Approach = Literal["rag", "rag_few_shot", "fine_tuning", "fine_tuning_classification"]

FEW_SHOT_THRESHOLD = 50


@dataclass
class ApproachRecommendation:
    approach: Approach
    reason: str


def recommend_approach(
    task_type: TaskType, has_documents: bool, qa_pair_count: int
) -> ApproachRecommendation:
    if task_type == "classification":
        return ApproachRecommendation(
            approach="fine_tuning_classification",
            reason=(
                "Классификация обращений — это отдельная задача обучения "
                "классификатора, а не генерации ответов."
            ),
        )

    if task_type == "style_writing":
        return ApproachRecommendation(
            approach="fine_tuning",
            reason=(
                "Чтобы модель писала в вашем стиле, ей нужно показать примеры "
                "этого стиля во время обучения — это именно то, для чего нужен "
                "fine-tuning."
            ),
        )

    # Remaining task types (support_qa, other) are fundamentally about
    # answering from known facts, where RAG is the default.
    if qa_pair_count == 0 and has_documents:
        return ApproachRecommendation(
            approach="rag",
            reason=(
                "У вас есть документы/база знаний — модель будет отвечать по "
                "ним напрямую, без обучения. Быстрее и дешевле, чем fine-tuning."
            ),
        )

    if 0 < qa_pair_count < FEW_SHOT_THRESHOLD:
        return ApproachRecommendation(
            approach="rag_few_shot",
            reason=(
                f"У вас {qa_pair_count} примеров — этого мало для качественного "
                "fine-tuning. Используем RAG и добавим ваши примеры прямо в "
                "подсказку модели (few-shot), чтобы она отвечала в похожем стиле."
            ),
        )

    if qa_pair_count >= FEW_SHOT_THRESHOLD:
        return ApproachRecommendation(
            approach="rag",
            reason=(
                f"У вас {qa_pair_count} примеров вопрос-ответ — этого достаточно, "
                "но для задачи \"отвечать по фактам\" RAG всё ещё быстрее и проще: "
                "не нужно переобучать модель, если факты изменятся."
            ),
        )

    return ApproachRecommendation(
        approach="rag",
        reason="Данных пока нет — начнём с пустой базы знаний, вы сможете добавить документы позже.",
    )
