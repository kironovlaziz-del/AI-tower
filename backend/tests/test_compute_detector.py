"""
Compute Detector: hardware tier recommendation and GPU detection.

_detect_gpu() is tested by injecting a fake `torch` module into
sys.modules (or forcing ImportError by setting it to None) so the tests
never depend on whether a real GPU or torch install exists on the box
running the suite.
"""

import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.services import compute_detector


# ---------------------------------------------------------------------------
# _recommend_tier - pure function, no mocking needed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "ram_gb,gpu_available,expected",
    [
        (2, False, "minimal"),
        (3.9, False, "minimal"),
        (4, False, "cpu_classic"),
        (7.9, False, "cpu_classic"),
        (8, False, "cpu_light_nlp"),
        (15.9, False, "cpu_light_nlp"),
        (16, False, "cpu_generous"),
        (64, False, "cpu_generous"),
        (2, True, "gpu"),  # GPU wins regardless of RAM
        (64, True, "gpu"),
    ],
)
def test_recommend_tier(ram_gb, gpu_available, expected):
    assert compute_detector._recommend_tier(ram_gb, gpu_available) == expected


# ---------------------------------------------------------------------------
# _detect_gpu
# ---------------------------------------------------------------------------

def test_detect_gpu_uses_torch_when_cuda_available(monkeypatch):
    fake_cuda = SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: 1,
        get_device_name=lambda i: "NVIDIA Fake GPU",
        mem_get_info=lambda i: (2 * 1024**3, 8 * 1024**3),  # (free, total) bytes
    )
    fake_torch = SimpleNamespace(cuda=fake_cuda)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    available, names, method, vram_total, vram_free = compute_detector._detect_gpu()

    assert available is True
    assert names == ["NVIDIA Fake GPU"]
    assert method == "torch"
    assert vram_total == 8.0
    assert vram_free == 2.0


def test_detect_gpu_falls_back_to_nvidia_smi_when_torch_reports_no_cuda(monkeypatch):
    fake_cuda = SimpleNamespace(is_available=lambda: False)
    fake_torch = SimpleNamespace(cuda=fake_cuda)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    monkeypatch.setattr(compute_detector.shutil, "which", lambda name: "/usr/bin/nvidia-smi")

    def fake_run(cmd, capture_output, text, timeout):
        if "--query-gpu=name" in cmd:
            return SimpleNamespace(returncode=0, stdout="Tesla T4\n")
        if "--query-gpu=memory.total,memory.free" in cmd:
            return SimpleNamespace(returncode=0, stdout="16384, 4096\n")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(compute_detector.subprocess, "run", fake_run)

    available, names, method, vram_total, vram_free = compute_detector._detect_gpu()

    assert available is True
    assert names == ["Tesla T4"]
    assert method == "nvidia-smi-after-torch"
    assert vram_total == 16.0
    assert vram_free == 4.0


def test_detect_gpu_no_torch_no_nvidia_smi_reports_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)  # forces ImportError on `import torch`
    monkeypatch.setattr(compute_detector.shutil, "which", lambda name: None)

    available, names, method, vram_total, vram_free = compute_detector._detect_gpu()

    assert available is False
    assert names == []
    assert method == "none"
    assert vram_total is None
    assert vram_free is None


def test_detect_gpu_nvidia_smi_present_but_returns_no_gpus(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setattr(compute_detector.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        compute_detector.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout=""),
    )

    available, names, method, vram_total, vram_free = compute_detector._detect_gpu()

    assert available is False
    assert names == []


def test_detect_gpu_handles_nvidia_smi_timeout_gracefully(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setattr(compute_detector.shutil, "which", lambda name: "/usr/bin/nvidia-smi")

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=5)

    monkeypatch.setattr(compute_detector.subprocess, "run", _timeout)

    available, names, method, vram_total, vram_free = compute_detector._detect_gpu()

    assert available is False
    assert method == "none"


# ---------------------------------------------------------------------------
# get_status() - full assembly, with psutil/shutil/_detect_gpu mocked out
# ---------------------------------------------------------------------------

def test_get_status_flags_low_disk_and_no_gpu_warnings(monkeypatch):
    monkeypatch.setattr(compute_detector.psutil, "cpu_count", lambda logical=True: 8 if logical else 4)
    monkeypatch.setattr(
        compute_detector.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=16 * 1024**3, available=8 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=100 * 1024**3, free=2 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector, "_detect_gpu", lambda: (False, [], "none", None, None)
    )

    status = compute_detector.get_status()

    assert status.cpu_logical_cores == 8
    assert status.cpu_physical_cores == 4
    assert status.ram_total_gb == 16.0
    assert status.gpu_available is False
    assert status.recommendation_tier == "cpu_generous"
    warning_codes = {w["code"] for w in status.warnings}
    assert "low_disk" in warning_codes
    assert "no_gpu" in warning_codes


def test_get_status_flags_low_vram_when_gpu_present_but_tight(monkeypatch):
    monkeypatch.setattr(compute_detector.psutil, "cpu_count", lambda logical=True: 16 if logical else 8)
    monkeypatch.setattr(
        compute_detector.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=32 * 1024**3, available=20 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=500 * 1024**3, free=100 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector,
        "_detect_gpu",
        lambda: (True, ["Fake GPU"], "torch", 8.0, 1.0),
    )

    status = compute_detector.get_status()

    assert status.gpu_available is True
    assert status.recommendation_tier == "gpu"
    warning_codes = {w["code"] for w in status.warnings}
    assert "low_vram" in warning_codes
    assert "no_gpu" not in warning_codes
    assert "low_disk" not in warning_codes


def test_get_status_no_warnings_on_a_healthy_machine(monkeypatch):
    monkeypatch.setattr(compute_detector.psutil, "cpu_count", lambda logical=True: 32 if logical else 16)
    monkeypatch.setattr(
        compute_detector.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=64 * 1024**3, available=48 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=1000 * 1024**3, free=500 * 1024**3),
    )
    monkeypatch.setattr(
        compute_detector,
        "_detect_gpu",
        lambda: (True, ["Fake GPU"], "torch", 24.0, 20.0),
    )

    status = compute_detector.get_status()

    assert status.warnings == []
