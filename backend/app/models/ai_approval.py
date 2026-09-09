from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from app.core.database import Base

class AIApproval(Base):
    __tablename__ = "ai_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False)
    approver_user_id = Column(Integer, ForeignKey("users.id"))
    decision = Column(String(20))  # approved, rejected
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

