"""Async SQLAlchemy engine + session factories.

This module is intentionally **unopinionated** — no module-level caches, no
hidden ``Settings`` access, no default pool sizes. Callers (the worker
runtime, Alembic, tests) own engine lifecycle and pass the resulting
``async_sessionmaker`` to consumers like :func:`session_scope`.

Rationale: a process-lifetime engine cached behind ``lru_cache`` keyed on a
mutable :class:`Settings` object is a footgun for tests and tools that need
their own database. Push lifecycle to the leaf (worker bootstrap).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


def create_engine(database_url: str, **engine_kwargs: object) -> AsyncEngine:
    """Build an :class:`AsyncEngine`.

    No defaults beyond SQLAlchemy's own — pass ``pool_size``, ``max_overflow``,
    ``pool_pre_ping`` etc. via ``engine_kwargs`` from the caller.

    Args:
        database_url: SQLAlchemy URL (e.g. ``postgresql+asyncpg://...``).
        engine_kwargs: Forwarded verbatim to :func:`create_async_engine`.
    """
    logger.debug("Creating async engine for database_url host=%s", _safe_host(database_url))
    return create_async_engine(database_url, **engine_kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to ``engine``.

    ``expire_on_commit=False`` so attributes loaded inside a unit of work
    remain readable after commit — usual choice for async services.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Provide a transactional async session from ``sessionmaker``.

    Commits on success, rolls back on exception, always closes the session.
    """
    session = sessionmaker()
    try:
        yield session
        await session.commit()
    except Exception:
        logger.exception("Session rolled back due to exception")
        await session.rollback()
        raise
    finally:
        await session.close()


def _safe_host(url: str) -> str:
    """Return ``host:port/db`` from a SQLAlchemy URL with credentials stripped.

    Used purely for log lines so we never accidentally leak the password
    component of a DSN.
    """
    # postgresql+asyncpg://user:pass@host:port/db -> host:port/db
    return url.rsplit("@", 1)[-1]
