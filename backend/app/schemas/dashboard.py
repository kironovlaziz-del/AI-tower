from pydantic import BaseModel
from typing import Dict, List


class DayBucket(BaseModel):
    date: str  # ISO date
    total: int
    completed: int
    blocked: int
    failed: int


class DashboardStats(BaseModel):
    # Aggregates over the window
    window_days: int

    # Time series
    requests_by_day: List[DayBucket]

    # Distribution maps
    requests_by_status: Dict[str, int]
    incidents_by_severity: Dict[str, int]
    training_by_status: Dict[str, int]
    deployments_by_status: Dict[str, int]

    # Scalar counters
    total_requests: int
    total_incidents: int
    total_training_jobs: int
    total_deployments: int
    active_deployments: int
    pending_approvals: int
    total_datasets: int
    total_policies: int
