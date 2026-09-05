from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class AIResponse(Base):
    __tablename__ = "ai_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False)
    provider_response_json = Column(JSONB)
    response_text = Column(Text)
    confidence_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
