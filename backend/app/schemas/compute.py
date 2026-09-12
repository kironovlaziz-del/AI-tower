from pydantic import BaseModel
from typing import List, Optional


class ComputeWarning(BaseModel):
    code: str
    disk_free_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None


class ComputeStatusOut(BaseModel):
    cpu_logical_cores: int
    cpu_physical_cores: Optional[int]
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    gpu_available: bool
    gpu_names: List[str]
    gpu_detection_method: str
    gpu_vram_total_gb: Optional[float] = None
    gpu_vram_free_gb: Optional[float] = None
    recommendation_tier: str
    warnings: List[ComputeWarning]