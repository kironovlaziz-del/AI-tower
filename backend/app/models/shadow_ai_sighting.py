from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.core.database import Base


class ShadowAISighting(Base):
    __tablename__ = "shadow_ai_sightings"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    tool_name = Column(String(255), nullable=False)
    domain = Column(String(255))
    detected_via = Column(String(50), default="manual")  # manual, expense_report, network_proxy, browser_extension, other
    user_hint = Column(String(255))  # email/name of the person reported to be using the tool
    notes = Column(Text)
    status = Column(String(20), default="new")  # new, reviewing, confirmed_shadow, dismissed, registered
    reported_by = Column(Integer, ForeignKey("users.id"))
    registered_provider_id = Column(Integer, ForeignKey("ai_providers.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
