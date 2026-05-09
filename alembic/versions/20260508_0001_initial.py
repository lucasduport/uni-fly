"""initial companion schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # gen_random_uuid() lives in pgcrypto on Postgres < 13 and as a builtin from
    # 13 onward. Creating the extension is harmless either way.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "bank_accounts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("account_type", sa.Text(), nullable=False),
        sa.Column("credentials_enc", sa.LargeBinary(), nullable=False),
        sa.Column("firefly_account_id", sa.Integer(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Document the encryption contract on the schema itself so Phase 5 can't
    # silently pick an incompatible format.
    op.execute(
        "COMMENT ON COLUMN bank_accounts.credentials_enc IS "
        "'Encrypted woob backend config. Format: AES-256-GCM via cryptography.Fernet "
        "(key sourced from ENCRYPTION_KEY env var). Decrypt with unifly_worker.security.crypto.'"
    )

    op.create_table(
        "sync_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "bank_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("firefly_transaction_id", sa.Integer(), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sync_log_bank_account_id", "sync_log", ["bank_account_id"])

    op.create_table(
        "classifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("firefly_transaction_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_category", sa.Text(), nullable=True),
        sa.Column("assigned_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_classifications_firefly_transaction_id",
        "classifications",
        ["firefly_transaction_id"],
    )

    op.create_table(
        "classification_examples",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=True),
        sa.Column("source_account", sa.Text(), nullable=True),
        sa.Column("correct_category", sa.Text(), nullable=False),
        sa.Column("correct_tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("classification_examples")
    op.drop_index("ix_classifications_firefly_transaction_id", "classifications")
    op.drop_table("classifications")
    op.drop_index("ix_sync_log_bank_account_id", "sync_log")
    op.drop_table("sync_log")
    op.drop_table("bank_accounts")
