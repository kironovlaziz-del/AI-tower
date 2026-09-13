from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class RequestCreate(BaseModel):
    use_case_id: int
    provider_id: int
    input_text: str
    purpose: str
    # ISO-639-1 code of the prompt's language. Optional: when omitted the
    # Prompt Firewall falls back to PROMPT_FIREWALL_NER_DEFAULT_LANG.
    language: Optional[str] = None


class RequestOut(BaseModel):
    id: int
    org_id: int
    use_case_id: Optional[int]
    user_id: Optional[int]
    provider_id: Optional[int]
    # The raw prompt is never exposed - operators only see the masked
    # version produced by the Prompt Firewall.
    masked_input_text: Optional[str]
    purpose: Optional[str]
    risk_level: str
    status: str
    firewall_flags: Optional[List[str]] = None
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
