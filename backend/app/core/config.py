from pydantic import model_validator
from pathlib import Path

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

    # Comma-separated list of allowed frontend origins for CORS. Never use
    # "*" together with allow_credentials=True - browsers reject it and it
    # lets any site make authenticated requests as the logged-in user.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"


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

    # Training isolation: when true, each training job runs in its own
    # Docker container built from backend/training_runner/. When false,
    # training runs in-process inside the Celery worker (the legacy
    # behaviour, useful for local development without Docker).
    TRAINING_USE_DOCKER: bool = False

    # Image used for isolated training jobs. Build it once with:
    #   docker build -t ai-control-tower/training-runner:latest backend/training_runner
    TRAINING_RUNNER_IMAGE: str = "ai-control-tower/training-runner:latest"

    # Container resource limits. Match these to the host's capacity.
    TRAINING_CONTAINER_CPUS: float = 2.0
    TRAINING_CONTAINER_MEMORY: str = "2g"

    # Prompt Firewall: enable NER-based PII detection (person names,
    # organizations, locations) on top of the built-in regex detectors.
    # Requires spaCy plus a language model; when the model is not
    # installed, NER is skipped silently.
    PROMPT_FIREWALL_NER_ENABLED: bool = True
    PROMPT_FIREWALL_NER_MODEL: str = "en_core_web_sm"

    # MLOps - relative paths are resolved against the project root
    # (backend/) so they work regardless of the current working directory.
    # Absolute paths from .env are used as-is.
    DATASETS_DIR: str = "data/datasets"
    MODELS_DIR: str = "data/models"

    # Connections: symmetric key used to encrypt provider API keys at rest.
    # Generate with:
    #   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Required in production.
    ENCRYPTION_KEY: str = ""

    # Optional: new key to rotate to. Set this alongside ENCRYPTION_KEY and
    # run scripts/rotate_encryption_key.py, then move the new value into
    # ENCRYPTION_KEY and clear this field. See README for details.
    ENCRYPTION_KEY_NEW: str = ""

    # Notification Service: email is optional
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ai-control-tower@localhost"
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        # Reject unknown variables in .env so a typo like "POSTGRESS_PASSWORD"
        # surfaces as a clear startup error instead of being silently ignored.
        extra = "forbid"

    @model_validator(mode="after")
    def _resolve_relative_paths(self):
        """
        Anchor MODELS_DIR and DATASETS_DIR to the backend package directory
        so that starting uvicorn from a different working directory does
        not silently create a second data/ tree somewhere else on disk.
        """
        backend_root = Path(__file__).resolve().parents[2]
        for field in ("DATASETS_DIR", "MODELS_DIR"):
            value = getattr(self, field)
            p = Path(value)
            if not p.is_absolute():
                setattr(self, field, str((backend_root / p).resolve()))
        return self

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
