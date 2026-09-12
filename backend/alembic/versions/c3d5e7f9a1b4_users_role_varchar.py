"""Convert users.role from PostgreSQL enum to VARCHAR

Revision ID: c3d5e7f9a1b4
Revises: a2c4e6f8b0d2
Create Date: 2026-09-12 01:00:00.000000

The dedicated `userrole` enum type is awkward to extend: adding a new role
requires ALTER TYPE ... ADD VALUE, which cannot run inside a transaction on
older PostgreSQL and does not autogenerate cleanly in Alembic. Switching to
a plain VARCHAR with application-level validation via Pydantic keeps the
schema flexible without sacrificing type safety at the API boundary.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d5e7f9a1b4"
down_revision: Union[str, None] = "a2c4e6f8b0d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast the enum column to text, then re-type the column as VARCHAR(50).
    op.alter_column(
        "users",
        "role",
        type_=sa.String(length=50),
        existing_type=sa.Enum(
            "admin", "approver", "user", name="userrole"
        ),
        postgresql_using="role::text",
        existing_nullable=True,
    )
    # Drop the now-unused enum type.
    op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE userrole AS ENUM ('admin', 'approver', 'user')"
    )
    op.alter_column(
        "users",
        "role",
        type_=sa.Enum("admin", "approver", "user", name="userrole"),
        existing_type=sa.String(length=50),
        postgresql_using="role::userrole",
        existing_nullable=True,
    )
