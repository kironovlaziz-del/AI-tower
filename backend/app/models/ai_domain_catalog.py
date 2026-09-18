from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from app.core.database import Base


class AIDomainCatalog(Base):
    """
    Per-organization catalog of known AI-service domains and their
    governance status (allowed/blocked/unknown). The ingestion pipeline
    matches incoming telemetry against this table (with suffix matching,
    so a catalog entry for "openai.com" also covers "chat.openai.com")
    to decide whether a detected domain should raise a Shadow AI sighting
    or an incident.
    """

    __tablename__ = "ai_domain_catalog"
    __table_args__ = (
        UniqueConstraint("org_id", "domain", name="uq_domain_catalog_org_domain"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    domain = Column(String(255), nullable=False)
    tool_name = Column(String(255))
    category = Column(String(100))
    policy_status = Column(String(20), default="unknown", nullable=False)  # allowed, blocked, unknown
    source = Column(String(20), default="manual")  # manual, seed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
