from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, Literal


class OverrideCreate(BaseModel):
    request_id: int
    override_type: Literal["stop", "edit", "rollback"]
    override_payload_json: Optional[Dict[str, Any]] = None


class OverrideOut(BaseModel):
    id: int
    request_id: int
    override_type: str
    override_payload_json: Optional[Dict[str, Any]]
    operator_user_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
