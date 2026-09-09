from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AIOverride(Base):
    __tablename__ = "ai_overrides"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False)
    override_type = Column(String(20), nullable=False)  # stop, edit, rollback
    override_payload_json = Column(JSONB)
    operator_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
