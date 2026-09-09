from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

SYNC_DATABASE_URL = (
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)
