from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    task_type = Column(String(30), nullable=False)  # tabular_classification, tabular_regression, transformer_text_classification
    target_column = Column(String(255), nullable=False)  # label column for tabular tasks, or text label column for transformer tasks
    algorithm = Column(String(50), nullable=True)  # sklearn track: logistic_regression, random_forest_classifier, linear_regression, random_forest_regressor
    base_model = Column(String(255), nullable=True)  # transformer track: HF model id, e.g. "distilbert-base-uncased"
    hyperparameters_json = Column(JSONB)
    feature_columns_json = Column(JSONB)  # filled in once training actually runs
    status = Column(String(20), default="queued")  # queued, running, completed, failed, cancelled
    metrics_json = Column(JSONB)
    model_path = Column(String(500))
    error_message = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
