from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    task_type = Column(String(50), nullable=False)  # tabular_classification, tabular_regression, transformer_text_classification, transformer_text_generation
    target_column = Column(String(255), nullable=True)  # label column for classification; unused (auto-filled) for generation
    algorithm = Column(String(50), nullable=True)  # sklearn track: logistic_regression, random_forest_classifier, linear_regression, random_forest_regressor
    base_model = Column(String(255), nullable=True)  # transformer track: HF model id, e.g. "distilbert-base-uncased"
    hyperparameters_json = Column(JSONB)
    feature_columns_json = Column(JSONB)  # filled in once training actually runs
    status = Column(String(20), default="queued")  # queued, running, completed, failed, cancelled
    celery_task_id = Column(String(255))
    metrics_json = Column(JSONB)
    model_path = Column(String(500))
    error_message = Column(Text)

    # Progress reporting during training: 0-100 plus a short stage label
    # ("Loading dataset", "Training step 42/120", ...). Updated by a
    # transformers TrainerCallback on every logging step, and by the
    # sklearn track at key checkpoints. NULL when the job has not started
    # or the value is unknown.
    progress_pct = Column(Float)
    progress_stage = Column(String(255))

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

    @property
    def has_model_artifact(self) -> bool:
        """True when a downloadable artifact exists on disk. The actual
        path stays server-side; the API only exposes this boolean."""
        return bool(self.model_path)
