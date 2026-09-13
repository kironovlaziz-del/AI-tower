from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class PredictionLog(Base):
    """
    Append-only log of every inference call through a deployment.

    One row per prediction. Features are stored as JSONB so monitoring
    can compute drift on arbitrary schemas; sensitive values are the
    caller's responsibility to mask before this point (see Prompt
    Firewall).
    """

    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    deployment_id = Column(
        Integer, ForeignKey("model_deployments.id"), nullable=False
    )
    # Snapshot of what went in (features) and what came out (prediction).
    features_json = Column(JSONB)
    prediction = Column(String(255))
    # Optional: user feedback (1 = correct, 0 = incorrect, null = unknown).
    feedback = Column(Integer)
    latency_ms = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
