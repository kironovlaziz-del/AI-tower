from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class AIAction(Base):
    __tablename__ = "ai_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    target_system = Column(String(255))
    action_payload_json = Column(JSONB)
    status = Column(String(50), default="pending")
    approved_by = Column(Integer, ForeignKey("users.id"))
    executed_at = Column(DateTime(timezone=True))

