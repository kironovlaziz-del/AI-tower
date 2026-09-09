from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, ForeignKey, func
from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(String(50), default="other")  # text_classification, regression, tabular, other
    file_format = Column(String(20))  # csv, json, txt, other
    file_path = Column(String(500), nullable=False)
    size_bytes = Column(BigInteger, default=0)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
