#!/usr/bin/env bash
set -e

echo "[entrypoint] waiting for postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-ai_user}" >/dev/null 2>&1; do
  sleep 1
done
echo "[entrypoint] postgres is ready"

echo "[entrypoint] running migrations..."
alembic upgrade head

# seed a demo organization + admin (idempotent — only if none exists)
echo "[entrypoint] seeding demo admin (if empty)..."
python3 -c "
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def seed():
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Organization).where(Organization.slug == 'demo'))
        if existing.scalar_one_or_none():
            print('[seed] demo org already exists, skipping')
            return
        org = Organization(name='Demo Organization', slug='demo')
        db.add(org)
        await db.flush()
        db.add(User(
            org_id=org.id, email='admin@demo.com', name='Demo Admin',
            hashed_password=get_password_hash('demo12345'),
            role=UserRole.admin.value, status='active',
        ))
        await db.commit()
        print('[seed] created demo org + admin@demo.com / demo12345')

asyncio.run(seed())
" || echo "[entrypoint] seed skipped or failed (non-fatal)"

echo "[entrypoint] starting: $@"
exec "$@"
