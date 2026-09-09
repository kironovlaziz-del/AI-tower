from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AIAuditLog(Base):
    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    entity_type = Column(String(50), nullable=False)  # policy, policy_version, use_case, provider, request, approval, incident, user
    entity_id = Column(Integer)
    action = Column(String(50), nullable=False)  # created, updated, approved, decided, blocked, ...
    metadata_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
