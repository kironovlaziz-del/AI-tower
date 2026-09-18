from pydantic import BaseModel
from typing import List, Optional


class ParsedQAPair(BaseModel):
    question: str
    answer: str


class ParseUploadResponse(BaseModel):
    qa_pairs: List[ParsedQAPair]
    error_row_count: int
    has_unstructured_text: bool
    detected_columns: Optional[List[str]] = None
    preview_text: Optional[str] = None
    # Convenience: the same recommendation Phase B's endpoint would give
    # for this exact data shape, so the wizard's screen 6 "Продолжить" can
    # act immediately without a second round trip.
    recommended_approach: str
    recommended_reason: str


class PreviewChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    provider_id: int


class PreviewChatResponse(BaseModel):
    answer: str


class FinalizeRAGPairIn(BaseModel):
    question: str
    answer: str


class FinalizeRAGResponse(BaseModel):
    collection_id: int
    document_statuses: List[str]
