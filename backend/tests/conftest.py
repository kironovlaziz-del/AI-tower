"""
Shared pytest fixtures.

Tests run against a dedicated `ai_control_tower_test` database. The schema
is created once per session via Alembic, and each test gets its own
transaction that is rolled back afterwards.
"""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Override the database name before importing the app so config picks it up.
os.environ["POSTGRES_DB"] = "ai_control_tower_test"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production-1234567890")
os.environ.setdefault("ENCRYPTION_KEY", "")  # dev fallback is fine in tests
os.environ.setdefault("REDIS_PASSWORD", "")

from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Organization, User, UserRole  # noqa: E402


TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/ai_control_tower_test"
)


# NOTE: pytest-asyncio 1.x manages the event loop itself based on
# asyncio_default_fixture_loop_scope / asyncio_default_test_loop_scope in
# pytest.ini. Overriding the event_loop fixture here is deprecated and
# breaks session-scoped async fixtures.

# ---------------------------------------------------------------------------
# Celery isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_celery_send_task(monkeypatch):
    """
    Prevent any test from actually dispatching work to Redis.

    Several API endpoints (request creation, approval decisions, training
    jobs) call `celery_app.send_task(...)`. Without a running worker and a
    reachable Redis, that raises during the request and masks the behaviour
    under test. Replacing send_task with a no-op keeps tests hermetic.
    """
    from app.core.celery_app import celery_app

    class _FakeResult:
        id = "test-task-id"

    def _fake_send_task(*args, **kwargs):
        return _FakeResult()

    monkeypatch.setattr(celery_app, "send_task", _fake_send_task)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        # Fresh schema per session. Alembic-driven would be cleaner but
        # also much slower for local iteration; drop_all + create_all
        # keeps the test cycle under a second.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped session bound to an outer transaction that is rolled
    back after the test. Endpoints run inside the same transaction thanks
    to the get_db override below.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session_maker = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_maker()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx client pointing at the FastAPI app. The get_db dependency is
    overridden so the API uses the same transactional session as the test.
    """

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org_with_admin_and_approver(
    db: AsyncSession,
    *,
    org_slug: str = "test-org",
    admin_email: str = "admin@test.example.com",
    approver_email: str = "approver@test.example.com",
    password: str = "TestPass123!",
) -> dict:
    from app.core.security import get_password_hash

    org = Organization(name="Test Org", slug=org_slug)
    db.add(org)
    await db.flush()

    admin = User(
        org_id=org.id,
        email=admin_email,
        name="Admin",
        hashed_password=get_password_hash(password),
        role=UserRole.admin.value,
        status="active",
    )
    approver = User(
        org_id=org.id,
        email=approver_email,
        name="Approver",
        hashed_password=get_password_hash(password),
        role=UserRole.approver.value,
        status="active",
    )
    db.add_all([admin, approver])
    await db.flush()
    return {
        "org": org,
        "admin": admin,
        "approver": approver,
        "password": password,
    }


@pytest_asyncio.fixture
async def org_and_users(db_session: AsyncSession) -> dict:
    return await _create_org_with_admin_and_approver(db_session)


async def _login(client: AsyncClient, org_slug: str, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"org_slug": org_slug, "email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, org_and_users: dict) -> str:
    return await _login(
        client,
        org_and_users["org"].slug,
        org_and_users["admin"].email,
        org_and_users["password"],
    )


@pytest_asyncio.fixture
async def approver_token(client: AsyncClient, org_and_users: dict) -> str:
    return await _login(
        client,
        org_and_users["org"].slug,
        org_and_users["approver"].email,
        org_and_users["password"],
    )


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
