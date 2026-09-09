from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class AIProvider(Base):
    __tablename__ = "ai_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # openai, anthropic, azure_openai, custom, etc.
    status = Column(String(50), default="active")
    sla = Column(String(255))
    risk_score = Column(Float, default=0.0)
    base_url = Column(String(500))
    default_model = Column(String(255))
    api_key_encrypted = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key_encrypted)
