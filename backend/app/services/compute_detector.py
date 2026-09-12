"""
Compute Detector

Reports what compute is actually available on this machine and translates
that into a hardware tier that the UI can render in the user's language.
The detector returns machine-readable codes only — no user-facing text —
so the frontend owns all localization via i18n.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    warnings: List[Dict[str, Any]] = field(default_factory=list)


def _detect_gpu() -> Tuple[bool, List[str], str, Optional[float], Optional[float]]:
    # Prefer torch if it happens to be installed - most accurate, and gives
    # us free memory too (via torch.cuda.mem_get_info).
    torch_says_no_gpu = False
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            vram_total_gb = round(total_bytes / (1024 ** 3), 2)
            vram_free_gb = round(free_bytes / (1024 ** 3), 2)
            return True, names, "torch", vram_total_gb, vram_free_gb
        # Torch installed but reports no CUDA - could still be a CPU-only
        # build on a machine that has an NVIDIA card. Fall through to
        # nvidia-smi rather than concluding "no GPU" too early.
        torch_says_no_gpu = True
    except ImportError:
        pass

    # Fall back to nvidia-smi presence, which works even without torch/CUDA
    # python bindings installed - tells us "there is NVIDIA hardware here"
    # even if the training stack isn't set up yet.
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
                    method = "nvidia-smi" if not torch_says_no_gpu else "nvidia-smi-after-torch"
                    return True, names, method, vram_total_gb, vram_free_gb
        except (subprocess.TimeoutExpired, OSError):
            pass

    method = "torch" if torch_says_no_gpu else "none"
    return False, [], method, None, None


def _recommend_tier(ram_gb: float, gpu_available: bool) -> str:
    """
    Returns only a machine-readable tier code. The human-readable text for
    each tier lives in the frontend i18n resources under
    `compute.recommendation.<tier>`.
    """
    if gpu_available:
        return "gpu"
    if ram_gb < 4:
        return "minimal"
    if ram_gb < 8:
        return "cpu_classic"
    if ram_gb < 16:
        return "cpu_light_nlp"
    return "cpu_generous"


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
    tier = _recommend_tier(ram_total_gb, gpu_available)

    warnings: List[Dict[str, Any]] = []
    if disk_free_gb < 5:
        warnings.append({"code": "low_disk", "disk_free_gb": disk_free_gb})
    if not gpu_available:
        warnings.append({"code": "no_gpu"})
    elif vram_free_gb is not None and vram_free_gb < 2:
        warnings.append({"code": "low_vram", "vram_free_gb": vram_free_gb})

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
        warnings=warnings,
    )