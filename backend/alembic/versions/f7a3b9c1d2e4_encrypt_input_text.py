"""Encrypt input_text at rest and add optional retention TTL

Revision ID: f7a3b9c1d2e4
Revises: e1f6a8b0c2d5
Create Date: 2026-09-12 00:00:00.000000

The raw prompt may contain PII that the Prompt Firewall masks before
sending to a provider. Storing the raw text in plaintext next to the
masked copy would defeat the firewall entirely, so the column is renamed
and its contents are now expected to be Fernet-encrypted.

Existing rows are cleared in this migration because they were stored
before encryption was introduced; the encryption key used at that time
is not available, so the plaintext cannot be safely re-wrapped.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a3b9c1d2e4"
down_revision: Union[str, None] = "e1f6a8b0c2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear existing plaintext before renaming — the old values would
    # otherwise linger as undecryptable strings.
    op.execute("UPDATE ai_requests SET input_text = NULL")

    op.alter_column(
        "ai_requests",
        "input_text",
        new_column_name="input_text_encrypted",
    )
    op.add_column(
        "ai_requests",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_requests", "retention_expires_at")
    op.alter_column(
        "ai_requests",
        "input_text_encrypted",
        new_column_name="input_text",
    )
