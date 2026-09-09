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
        "id": "prajjwal1/bert-tiny",
        "label": "BERT-Tiny (~4M параметров)",
        "note": "Самый быстрый вариант на CPU - минуты, а не часы, на небольших датасетах.",
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

# Safety margin: require this multiple of the estimate to be free, since the
# estimate doesn't account for activation memory growing with batch size,
# CUDA context overhead, or other processes sharing the GPU.
VRAM_SAFETY_MARGIN = 1.3


def allowed_models(gpu_available: bool, gpu_vram_free_gb: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Returns the curated model list, annotated with whether each one
    currently fits in the detected free VRAM (fits_vram: true/false/null).
    null means "unknown" - either no GPU, or VRAM couldn't be read.
    """
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
    model_id: str, gpu_available: bool, gpu_vram_free_gb: Optional[float] = None
) -> Dict[str, Any]:
    """
    Validates a specific model choice against detected hardware.
    Returns {"allowed": bool, "reason": str|None}.
    """
    all_curated = CPU_SAFE_MODELS + GPU_ADDITIONAL_MODELS
    match = next((m for m in all_curated if m["id"] == model_id), None)

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
