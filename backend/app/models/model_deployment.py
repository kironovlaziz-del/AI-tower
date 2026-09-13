from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from app.core.database import Base


class ModelDeployment(Base):
    """
    A deployment wraps a trained model (TrainingJob) in a stable endpoint
    with a version and lifecycle status, so callers can send inference
    requests without knowing how the underlying artifact is stored.

    Status:
      - "active"    accepting traffic
      - "inactive"  temporarily paused, still kept in the registry
      - "archived"  retired, kept for historical reference

    Version is scoped per (org_id, name): deploying "Sentiment" twice
    creates v1 and v2. traffic_weight is reserved for future A/B routing
    (only relevant once more than one deployment shares a name).
    """

    __tablename__ = "model_deployments"

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "name",
            "version",
            name="uq_model_deployments_org_name_version",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    training_job_id = Column(
        Integer, ForeignKey("training_jobs.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="active")
    # Reserved for A/B routing. 1.0 = receive all traffic among same-name
    # deployments; a share between them will be used once routing lands.
    traffic_weight = Column(Float, nullable=False, default=1.0)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
