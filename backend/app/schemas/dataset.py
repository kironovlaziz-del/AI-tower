from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DatasetOut(BaseModel):
    id: int
    org_id: int
    name: str
    description: Optional[str]
    task_type: str
    file_format: Optional[str]
    size_bytes: int
    uploaded_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
