from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class RequestCreate(BaseModel):
    use_case_id: int
    provider_id: int
    input_text: str
    purpose: str

class RequestOut(BaseModel):
    id: int
    org_id: int
    use_case_id: Optional[int]
    user_id: Optional[int]
    provider_id: Optional[int]
    input_text: Optional[str]
    masked_input_text: Optional[str]
    purpose: Optional[str]
    risk_level: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResponseOut(BaseModel):
    id: int
    request_id: int
    provider_response_json: Optional[Dict[str, Any]]
    response_text: Optional[str]
    confidence_score: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True
