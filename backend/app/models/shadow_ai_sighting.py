from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
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
    # Human-readable specifics for display, populated by the telemetry
    # pipeline from the collector's payload: for a local process this is
    # {process_name, pid, ai_tool}; for a listening port {port, service};
    # for a model file {file_name, size_mb}; plus agent_id (device name)
    # where present. The domain column keeps the raw dedup key (e.g.
    # "local:host:port:8000") which is NOT meant for humans - display_meta
    # is what the UI actually renders.
    display_meta = Column(JSONB)
    # Repeat-detection: rather than spawning a new sighting for every
    # re-observation of the same tool (which the dedup logic suppresses),
    # we count how many times it's been seen and when last - so the UI can
    # show "seen 12 times, last seen 2h ago", which is the signal that a
    # tool is in active ongoing use vs a one-off.
    seen_count = Column(Integer, nullable=False, default=1, server_default="1")
    last_seen_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))


