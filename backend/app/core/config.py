from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Control Tower"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_USER: str = "ai_user"
    POSTGRES_PASSWORD: str = "ai_password"
    POSTGRES_DB: str = "ai_control_tower"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MLOps
    DATASETS_DIR: str = "./data/datasets"
    MODELS_DIR: str = "./data/models"

    # Connections: symmetric key used to encrypt provider API keys at rest.
    # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Notification Service: email is optional - if SMTP_HOST is left empty,
    # email notifications are skipped silently (webhook notifications still
    # work without any of this configured).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ai-control-tower@localhost"
    SMTP_USE_TLS: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
