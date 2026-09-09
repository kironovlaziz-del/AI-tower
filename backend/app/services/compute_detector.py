"""
Compute Detector

Reports what compute is actually available on this machine and translates
that into a plain-language statement of what training workloads are
realistic here. The goal is to stop a person from picking "fine-tune a 7B
LLM" on a box that can't do it, before they waste hours finding out the
hard way.

No GPU detection library is assumed to be installed (torch is NOT a
dependency of this backend by default - installing it is a deliberate,
heavy decision left for when actual training is wired up). Detection here
is import-optional and falls back to shelling out to `nvidia-smi`, which is
enough to tell "no NVIDIA GPU present" from "GPU present, driver stack not
yet installed".
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

import psutil


@dataclass
class ComputeStatus:
    cpu_logical_cores: int
    cpu_physical_cores: Optional[int]
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    gpu_available: bool
    gpu_names: List[str] = field(default_factory=list)
    gpu_detection_method: str = "none"
    gpu_vram_total_gb: Optional[float] = None
    gpu_vram_free_gb: Optional[float] = None
    recommendation_tier: str = ""
    recommendation_detail: str = ""
    warnings: List[str] = field(default_factory=list)


def _detect_gpu() -> "tuple[bool, List[str], str, Optional[float], Optional[float]]":
    # Prefer torch if it happens to be installed - most accurate, and gives
    # us free memory too (via torch.cuda.mem_get_info).
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            vram_total_gb = round(total_bytes / (1024 ** 3), 2)
            vram_free_gb = round(free_bytes / (1024 ** 3), 2)
            return True, names, "torch", vram_total_gb, vram_free_gb
        return False, [], "torch", None, None
    except ImportError:
        pass

    # Fall back to nvidia-smi presence, which works even without torch/CUDA
    # python bindings installed - tells us "there is NVIDIA hardware here"
    # even if the training stack isn't set up yet. This also gives us VRAM
    # numbers via a second nvidia-smi query.
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if names:
                    vram_total_gb = None
                    vram_free_gb = None
                    try:
                        mem_result = subprocess.run(
                            [
                                "nvidia-smi",
                                "--query-gpu=memory.total,memory.free",
                                "--format=csv,noheader,nounits",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if mem_result.returncode == 0:
                            first_line = mem_result.stdout.strip().splitlines()[0]
                            total_mib, free_mib = [
                                float(x.strip()) for x in first_line.split(",")
                            ]
                            vram_total_gb = round(total_mib / 1024, 2)
                            vram_free_gb = round(free_mib / 1024, 2)
                    except (subprocess.TimeoutExpired, OSError, ValueError, IndexError):
                        pass
                    return True, names, "nvidia-smi", vram_total_gb, vram_free_gb
        except (subprocess.TimeoutExpired, OSError):
            pass

    return False, [], "none", None, None


def _recommend(ram_gb: float, gpu_available: bool, gpu_names: List[str]) -> "tuple[str, str]":
    if gpu_available:
        return (
            "gpu",
            "GPU обнаружен ("
            + ", ".join(gpu_names)
            + "). В зависимости от объёма видеопамяти можно рассматривать "
            "fine-tuning с LoRA/QLoRA для моделей вплоть до 7-13 млрд параметров, "
            "либо полное обучение моделей меньшего размера. Конкретный список "
            "доступных моделей рассчитывается по реальной свободной VRAM, "
            "см. /compute/allowed-models.",
        )

    if ram_gb < 4:
        return (
            "minimal",
            "GPU не обнаружен, доступной RAM меньше 4 ГБ. Реалистичны только "
            "простейшие классические модели (логистическая регрессия, "
            "неглубокие деревья решений) на небольших табличных датасетах. "
            "Fine-tuning любых NLP/LLM моделей на этом сервере не рекомендуется.",
        )
    if ram_gb < 8:
        return (
            "cpu_classic",
            "GPU не обнаружен, RAM ограничена. Хорошо подходит классический "
            "ML (scikit-learn, XGBoost) на табличных данных. Инференс "
            "небольших NLP-моделей (DistilBERT-класса) возможен, но их "
            "обучение на CPU будет медленным и годится только для очень "
            "маленьких датасетов.",
        )
    if ram_gb < 16:
        return (
            "cpu_light_nlp",
            "GPU не обнаружен, но RAM достаточно для классического ML в "
            "полном объёме. Лёгкий fine-tuning совсем небольших NLP-моделей "
            "на CPU технически возможен, но будет занимать часы даже на "
            "скромных датасетах - используйте это только для экспериментов, "
            "не для регулярного обучения.",
        )
    return (
        "cpu_generous",
        "GPU не обнаружен, но объём RAM достаточно большой. Классический ML "
        "без практических ограничений по памяти. CPU-обучение небольших "
        "transformer-моделей возможно, однако по скорости остаётся на "
        "порядки медленнее GPU - для серьёзного fine-tuning LLM "
        "по-прежнему рекомендуется облачный GPU.",
    )


def get_status() -> ComputeStatus:
    cpu_logical = psutil.cpu_count(logical=True) or 1
    cpu_physical = psutil.cpu_count(logical=False)

    vm = psutil.virtual_memory()
    ram_total_gb = round(vm.total / (1024 ** 3), 2)
    ram_available_gb = round(vm.available / (1024 ** 3), 2)

    disk = shutil.disk_usage("/")
    disk_total_gb = round(disk.total / (1024 ** 3), 2)
    disk_free_gb = round(disk.free / (1024 ** 3), 2)

    gpu_available, gpu_names, gpu_method, vram_total_gb, vram_free_gb = _detect_gpu()
    tier, detail = _recommend(ram_total_gb, gpu_available, gpu_names)

    warnings: List[str] = []
    if disk_free_gb < 5:
        warnings.append(
            f"Свободного места на диске мало ({disk_free_gb} ГБ) - "
            "загрузка датасетов или сохранение артефактов моделей может не пройти."
        )
    if not gpu_available:
        warnings.append(
            "GPU не обнаружен: fine-tuning больших LLM (даже с LoRA/QLoRA) "
            "на этом сервере невозможен. Рассмотрите облачный GPU для таких задач."
        )
    elif vram_free_gb is not None and vram_free_gb < 2:
        warnings.append(
            f"Свободной VRAM мало ({vram_free_gb} ГБ) - даже маленькие "
            "модели могут не поместиться, особенно если на GPU уже что-то "
            "выполняется."
        )

    return ComputeStatus(
        cpu_logical_cores=cpu_logical,
        cpu_physical_cores=cpu_physical,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        disk_total_gb=disk_total_gb,
        disk_free_gb=disk_free_gb,
        gpu_available=gpu_available,
        gpu_names=gpu_names,
        gpu_detection_method=gpu_method,
        gpu_vram_total_gb=vram_total_gb,
        gpu_vram_free_gb=vram_free_gb,
        recommendation_tier=tier,
        recommendation_detail=detail,
        warnings=warnings,
    )
