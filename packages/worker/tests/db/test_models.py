"""Tests for the companion DB models + Alembic migration.

Unit-level tests just import the package and assert the metadata is wired up.
The full migration is exercised against a real Postgres via the
``integration`` marker, run separately:

    DATABASE_URL=postgresql+asyncpg://companion:<password>@localhost:5432/companion \
        uv run pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from unifly_worker.db.base import Base
from unifly_worker.db.models import (
    BankAccount,
    Classification,
    ClassificationExample,
    SyncLog,
)


def test_metadata_contains_all_phase_one_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {
        "bank_accounts",
        "sync_log",
        "classifications",
        "classification_examples",
    }.issubset(table_names)


def test_models_expose_expected_columns() -> None:
    assert "provider" in BankAccount.__table__.columns
    assert "external_id" in SyncLog.__table__.columns
    assert SyncLog.__table__.columns["external_id"].unique is True
    assert "assigned_tags" in Classification.__table__.columns
    assert "correct_category" in ClassificationExample.__table__.columns


def test_timestamps_are_timezone_aware() -> None:
    """All datetime columns must be tz-aware (Postgres ``timestamptz``)."""
    for table in (BankAccount, SyncLog, Classification, ClassificationExample):
        for column in table.__table__.columns:
            python_type_name = type(column.type).__name__
            if python_type_name == "DateTime":
                assert column.type.timezone is True, (  # type: ignore[attr-defined]
                    f"{table.__tablename__}.{column.name} must be DateTime(timezone=True)"
                )


def test_sync_log_fk_uses_restrict_not_cascade() -> None:
    """Audit trail must not be silently destroyed when a bank account is removed."""
    fk = next(iter(SyncLog.__table__.columns["bank_account_id"].foreign_keys))
    assert fk.ondelete == "RESTRICT"


def test_indexes_present_on_hot_lookup_columns() -> None:
    sync_log_indexed = {col.name for idx in SyncLog.__table__.indexes for col in idx.columns}
    classifications_indexed = {
        col.name for idx in Classification.__table__.indexes for col in idx.columns
    }
    assert "bank_account_id" in sync_log_indexed
    assert "firefly_transaction_id" in classifications_indexed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_applies_against_postgres() -> None:
    """End-to-end: alembic upgrade head must succeed against a real Postgres.

    Skipped by default. Bring up the stack first:

        docker compose up -d companion-db
        DATABASE_URL=postgresql+asyncpg://companion:<password>@localhost:5432/companion \
            uv run pytest -m integration
    """
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as conn:
            tables: set[str] = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
            await conn.execute(text("SELECT 1"))
    finally:
        await engine.dispose()

    assert {
        "bank_accounts",
        "sync_log",
        "classifications",
        "classification_examples",
        "alembic_version",
    }.issubset(tables)
