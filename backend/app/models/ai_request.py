from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class AIRequest(Base):
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    use_case_id = Column(Integer, ForeignKey("ai_use_cases.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    provider_id = Column(Integer, ForeignKey("ai_providers.id"))
    input_text = Column(Text)
    masked_input_text = Column(Text)
    purpose = Column(String(255))
    risk_level = Column(String(20), default="low")
    status = Column(String(50), default="pending")  # pending, pending_approval, blocked, approved, rejected, completed, failed
    firewall_flags = Column(JSONB)  # e.g. ["masked:email", "blocked_term:foo"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
