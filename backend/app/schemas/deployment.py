from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Any, Dict, Optional


class DeploymentCreate(BaseModel):
    # Accept extra=False so a typo in a client payload fails loudly.
    model_config = ConfigDict(extra="forbid")

    training_job_id: int
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    # Optional: pin a version. When omitted, the service picks the next
    # available version for this (org, name).
    version: Optional[int] = None
    traffic_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class DeploymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(active|inactive|archived)$")
    traffic_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class DeploymentOut(BaseModel):
    id: int
    org_id: int
    training_job_id: int
    name: str
    version: int
    description: Optional[str]
    status: str
    traffic_weight: float
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeploymentPredictRequest(BaseModel):
    features: Dict[str, Any]


class DeploymentPredictResponse(BaseModel):
    deployment_id: int
    version: int
    prediction: Any


class DeploymentChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)


class DeploymentChatResponse(BaseModel):
    deployment_id: int
    version: int
    model_type: str  # transformer_text_classification / transformer_text_generation
    response: str
    latency_ms: int
    raw: Any = None
