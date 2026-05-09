"""Alembic environment — async-aware, reads DATABASE_URL directly from env.

Intentionally does not import :mod:`unifly_worker.config` so the migration
tool can run in lean containers (the compose ``alembic`` service does not
need the worker package's pydantic-settings stack just to read one env var).
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import models so Base.metadata is populated for autogenerate.
from unifly_worker.db import models  # noqa: F401
from unifly_worker.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    database_url = os.environ["DATABASE_URL"]
except KeyError as exc:  # pragma: no cover - operational error path
    msg = "DATABASE_URL must be set in the environment to run Alembic"
    raise RuntimeError(msg) from exc

config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Render migration SQL without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    """Run migrations against a live async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
