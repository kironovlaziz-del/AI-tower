"""add organizations.slug; make users.email unique per organization

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c1
Create Date: 2026-09-12 03:00:00.000000
"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:63] or "org"


def upgrade() -> None:
    # 1. Add the slug column, nullable at first so we can backfill.
    op.add_column(
        "organizations",
        sa.Column("slug", sa.String(length=63), nullable=True),
    )

    # 2. Backfill slugs from the organization name, resolving collisions.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, name FROM organizations ORDER BY id")
    ).fetchall()
    used: set[str] = set()
    for row_id, name in rows:
        base = _slugify(name)
        candidate = base
        n = 2
        while candidate in used:
            candidate = f"{base[:60]}-{n}"
            n += 1
        used.add(candidate)
        connection.execute(
            sa.text("UPDATE organizations SET slug = :slug WHERE id = :id"),
            {"slug": candidate, "id": row_id},
        )

    # 3. Enforce NOT NULL + UNIQUE now that every row has a value.
    op.alter_column(
        "organizations",
        "slug",
        existing_type=sa.String(length=63),
        nullable=False,
    )
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])

    # 4. Drop the global unique index on users.email and add a
    #    per-organization uniqueness constraint instead.
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_unique_constraint(
        "uq_users_org_email", "users", ["org_id", "email"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_org_email", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.drop_constraint("uq_organizations_slug", "organizations", type_="unique")
    op.drop_column("organizations", "slug")
