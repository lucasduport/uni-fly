"""Tests for the WorkerRuntime container."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from unifly_worker.config import Settings
from unifly_worker.runtime import WorkerRuntime


def _settings() -> Settings:
    """Postgres URL — engine creation is lazy, no connection is opened in tests."""
    return Settings(
        firefly_url="http://localhost:8080",
        firefly_token="tok",
        mistral_api_key="key",
        database_url="postgresql+asyncpg://x:y@localhost:5432/z",
    )


async def test_from_settings_builds_engine_and_sessionmaker() -> None:
    rt = WorkerRuntime.from_settings(_settings())
    try:
        assert isinstance(rt.engine, AsyncEngine)
        assert isinstance(rt.sessionmaker, async_sessionmaker)
        assert rt.settings.firefly_url == "http://localhost:8080"
    finally:
        await rt.aclose()


async def test_runtime_context_manager_disposes_engine() -> None:
    async with WorkerRuntime.from_settings(_settings()) as rt:
        assert rt.engine is not None
    # Disposing twice is a no-op.
    await rt.aclose()


async def test_runtime_is_immutable() -> None:
    """Frozen dataclass — setting attributes must raise."""
    rt = WorkerRuntime.from_settings(_settings())
    try:
        try:
            rt.settings = _settings()  # type: ignore[misc]
        except (AttributeError, TypeError):
            pass
        else:
            msg = "WorkerRuntime should be frozen"
            raise AssertionError(msg)
    finally:
        await rt.aclose()


async def test_pool_kwargs_are_forwarded() -> None:
    """pool_size / max_overflow must be tunable from the leaf, not core."""
    rt = WorkerRuntime.from_settings(_settings(), pool_size=2, max_overflow=1)
    try:
        # SQLAlchemy QueuePool exposes the configured size.
        assert rt.engine.pool.size() == 2  # type: ignore[attr-defined]
    finally:
        await rt.aclose()
