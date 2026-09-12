from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Control Tower"
    API_V1_STR: str = "/api/v1"

    # "development" | "production". In production, insecure defaults for
    # SECRET_KEY and ENCRYPTION_KEY are rejected at startup, and /docs is
    # disabled. Set ENVIRONMENT=production in backend/.env on any real
    # deployment.
    ENVIRONMENT: str = "development"

    # When true, SQLAlchemy logs every SQL statement. Off by default;
    # enable for local debugging only.
    DEBUG: bool = False

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

    # JWT - must be overridden in production
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MLOps
    DATASETS_DIR: str = "./data/datasets"
    MODELS_DIR: str = "./data/models"

    # Connections: symmetric key used to encrypt provider API keys at rest.
    # Generate with:
    #   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Required in production.
    ENCRYPTION_KEY: str = ""

    # Notification Service: email is optional
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ai-control-tower@localhost"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def _enforce_production_secrets(self):
        """
        Refuse to start in production with insecure default secrets. This
        prevents a copy-pasted .env.example from quietly running with a
        well-known JWT key or an empty Fernet key.
        """
        if self.ENVIRONMENT != "production":
            return self

        problems: list[str] = []

        if self.SECRET_KEY == "your-secret-key-change-in-production":
            problems.append(
                "SECRET_KEY is still the default. Generate a long random string "
                "and set it in backend/.env before deploying."
            )
        if len(self.SECRET_KEY) < 32:
            problems.append(
                "SECRET_KEY is shorter than 32 characters - too weak for HS256."
            )
        if not self.ENCRYPTION_KEY:
            problems.append(
                "ENCRYPTION_KEY is empty. Generate one with "
                "'python3 -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\"'."
            )
        if self.POSTGRES_PASSWORD in ("", "ai_password", "change_me_in_dot_env"):
            problems.append(
                "POSTGRES_PASSWORD is still a default value."
            )
        if not self.REDIS_PASSWORD:
            problems.append("REDIS_PASSWORD is empty.")

        if problems:
            raise ValueError(
                "Refusing to start with ENVIRONMENT=production and insecure "
                "configuration:\n  - " + "\n  - ".join(problems)
            )

        return self


settings = Settings()
