from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from app.core.database import Base


class IngestionSource(Base):
    """
    A machine identity for an external telemetry collector (Gateway
    DNS/SSL tap, endpoint daemon, browser extension) that pushes events
    into POST /shadow-ai/ingest.

    Authenticated via a hashed API key (X-Ingestion-Key header) rather
    than a user JWT - these are not human sessions, and treating them as
    one would make the audit log misleadingly attribute machine activity
    to whichever user's token happened to be reused.
    """

    __tablename__ = "ingestion_sources"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(30), nullable=False)  # gateway, endpoint, browser_extension
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    last_seen_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
