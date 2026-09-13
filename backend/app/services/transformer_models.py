"""
Model allow-list for the transformer fine-tuning track.

Kept deliberately small and curated rather than letting people type any
Hugging Face model id on a CPU-only box - a bad choice there doesn't fail
fast, it just hangs for hours. Once a GPU is present, the actual free VRAM
is checked against a conservative estimate of what full fine-tuning needs
(fp32 weights + gradients + Adam optimizer state is roughly 16 bytes per
parameter, plus headroom for activations) - this is a soft pre-flight
check, not a guarantee: VRAM fragmentation or other processes on the GPU
can still cause an out-of-memory error at train time, which
training_tasks.py catches separately and reports clearly.
"""

from typing import Any, Dict, List, Optional

# estimated_vram_gb is a conservative estimate for full fine-tuning at a
# modest batch size (~8) and sequence length (~256) in fp32.
CPU_SAFE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "google/bert_uncased_L-2_H-128_A-2",
        "label": "BERT-Tiny Google (~4M параметров)",
        "note": "Самый быстрый вариант на CPU - минуты, а не часы, на небольших датасетах. Официальный релиз Google с полным набором файлов токенизатора.",
        "estimated_vram_gb": 0.3,
    },
    {
        "id": "microsoft/MiniLM-L12-H384-uncased",
        "label": "MiniLM-L12 (~33M параметров)",
        "note": "Компромисс скорость/качество, всё ещё практично на CPU.",
        "estimated_vram_gb": 1.0,
    },
    {
        "id": "distilbert-base-uncased",
        "label": "DistilBERT (~66M параметров)",
        "note": "Заметно медленнее на CPU - рассчитывайте на десятки минут - часы даже на маленьком датасете.",
        "estimated_vram_gb": 2.0,
    },
]

GPU_ADDITIONAL_MODELS: List[Dict[str, Any]] = [
    {
        "id": "bert-base-uncased",
        "label": "BERT-base (~110M параметров)",
        "note": "Требует GPU для практичного времени обучения.",
        "estimated_vram_gb": 3.0,
    },
    {
        "id": "roberta-base",
        "label": "RoBERTa-base (~125M параметров)",
        "note": "Требует GPU для практичного времени обучения.",
        "estimated_vram_gb": 3.5,
    },
]

# Models suitable for causal language modeling (text generation).
# Small enough to train on CPU for demos; larger ones need a GPU.
GENERATION_MODELS: List[Dict[str, Any]] = [
    {
        "id": "sshleifer/tiny-gpt2",
        "label": "Tiny GPT-2 (~2M параметров)",
        "note": "Игрушечная модель, годится только для проверки пайплайна.",
        "estimated_vram_gb": 0.2,
    },
    {
        "id": "distilgpt2",
        "label": "DistilGPT-2 (~82M параметров)",
        "note": "Быстрая генерация на CPU; качество ниже, чем у полноценного GPT-2.",
        "estimated_vram_gb": 2.5,
    },
    {
        "id": "gpt2",
        "label": "GPT-2 (~124M параметров)",
        "note": "Базовый GPT-2; для практичного времени обучения нужен GPU.",
        "estimated_vram_gb": 4.0,
    },
]

# Safety margin: require this multiple of the estimate to be free, since the
# estimate doesn't account for activation memory growing with batch size,
# CUDA context overhead, or other processes sharing the GPU.
VRAM_SAFETY_MARGIN = 1.3


def allowed_models(
    gpu_available: bool,
    gpu_vram_free_gb: Optional[float] = None,
    task_type: str = "transformer_text_classification",
) -> List[Dict[str, Any]]:
    """
    Returns the curated model list for the given task type, annotated with
    whether each model currently fits in the detected free VRAM
    (fits_vram: true/false/null). null means "unknown" - either no GPU, or
    VRAM couldn't be read.
    """
    if task_type == "transformer_text_generation":
        candidates = list(GENERATION_MODELS)
        if gpu_available:
            candidates += [
                m for m in GENERATION_MODELS if m["estimated_vram_gb"] >= 3.0
            ]
    else:
        candidates = CPU_SAFE_MODELS + GPU_ADDITIONAL_MODELS if gpu_available else list(CPU_SAFE_MODELS)
    result = []
    for m in candidates:
        entry = dict(m)
        if gpu_available and gpu_vram_free_gb is not None:
            required = m["estimated_vram_gb"] * VRAM_SAFETY_MARGIN
            entry["fits_vram"] = gpu_vram_free_gb >= required
        else:
            entry["fits_vram"] = None
        result.append(entry)
    return result


def check_model_fit(
    model_id: str,
    task_type: str,
    gpu_available: bool,
    gpu_vram_free_gb: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Validates a specific model choice against detected hardware and the
    requested task type. Returns {"allowed": bool, "reason": str|None}.

    The task type determines which curated list is authoritative: a model
    that exists in GENERATION_MODELS is not valid for classification, and
    vice versa.
    """
    if task_type == "transformer_text_generation":
        candidates = list(GENERATION_MODELS)
    else:
        candidates = CPU_SAFE_MODELS + GPU_ADDITIONAL_MODELS

    match = next((m for m in candidates if m["id"] == model_id), None)

    if match is None:
        # Not in the curated list: only trust a free-form model id if a GPU
        # is present, and we can't estimate its VRAM need, so just warn.
        if gpu_available:
            return {
                "allowed": True,
                "reason": (
                    "Модель не из курируемого списка - объём необходимой "
                    "VRAM неизвестен, возможен OOM во время обучения."
                ),
            }
        return {
            "allowed": False,
            "reason": "Эта модель не разрешена без GPU. Выберите модель из списка для CPU.",
        }

    if not gpu_available and match in GPU_ADDITIONAL_MODELS:
        return {"allowed": False, "reason": f"'{model_id}' требует GPU."}

    if gpu_available and gpu_vram_free_gb is not None:
        required = match["estimated_vram_gb"] * VRAM_SAFETY_MARGIN
        if gpu_vram_free_gb < required:
            return {
                "allowed": False,
                "reason": (
                    f"Недостаточно свободной VRAM: нужно ~{required:.1f} ГБ "
                    f"(с запасом), доступно {gpu_vram_free_gb:.1f} ГБ."
                ),
            }

    return {"allowed": True, "reason": None}


def is_model_allowed(model_id: str, gpu_available: bool, gpu_vram_free_gb: Optional[float] = None) -> bool:
    return check_model_fit(model_id, gpu_available, gpu_vram_free_gb)["allowed"]
