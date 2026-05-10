"""ORM models for the companion database.

Schema mirrors ``uni-fly-plan.md`` § Companion DB Schema. **Postgres only** —
``UUID``, ``BYTEA``, and ``ARRAY(Text)`` are Postgres-specific types. Tests
that exercise the schema run against a real Postgres via the ``integration``
marker; SQLite is not supported and unit tests stay metadata-only.

UUID primary keys are generated server-side via ``gen_random_uuid()`` (pgcrypto
extension installed by the initial migration). The ORM does not provide a
client-side fallback — pushing IDs into the database keeps a single source of
truth and avoids divergence between application-generated and DB-generated
identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from unifly_worker.db.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    account_type: Mapped[str] = mapped_column(Text, nullable=False)
    # Encryption format/key sourcing is owned by Phase 5; treat as opaque BYTEA
    # at this layer. See migration COMMENT for the agreed contract.
    credentials_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    firefly_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # RESTRICT: deleting a bank account with sync history must be a
        # deliberate operator action — sync_log is audit data, not cache.
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    firefly_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    firefly_transaction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClassificationExample(Base):
    __tablename__ = "classification_examples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source_account: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_category: Mapped[str] = mapped_column(Text, nullable=False)
    correct_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
