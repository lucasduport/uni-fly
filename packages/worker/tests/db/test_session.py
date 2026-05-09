"""Tests for the unopinionated DB session helpers.

The session module must NOT have module-level state — every test should be
free to construct its own engine + sessionmaker without contaminating others.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from unifly_worker.db import session as session_module
from unifly_worker.db.session import create_engine, make_sessionmaker, session_scope


async def test_create_engine_returns_async_engine_and_passes_kwargs() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:", future=True)
    try:
        assert isinstance(engine, AsyncEngine)
    finally:
        await engine.dispose()


async def test_make_sessionmaker_binds_to_engine() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    try:
        sm = make_sessionmaker(engine)
        assert isinstance(sm, async_sessionmaker)
        async with sm() as session:
            assert session.bind is engine
    finally:
        await engine.dispose()


async def test_session_scope_commits_on_success() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    try:
        sm = make_sessionmaker(engine)
        async with session_scope(sm) as session:
            assert session.is_active
        # Re-entering should still work — no shared state.
        async with session_scope(sm) as session2:
            assert session2.is_active
    finally:
        await engine.dispose()


async def test_session_scope_rolls_back_on_exception() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    try:
        sm = make_sessionmaker(engine)
        with pytest.raises(RuntimeError, match="boom"):
            async with session_scope(sm) as session:
                assert session.is_active
                raise RuntimeError("boom")
    finally:
        await engine.dispose()


def test_session_module_has_no_lru_cache() -> None:
    """Regression guard: session.py must not reintroduce module-level caches."""
    public_callables = {
        name
        for name in dir(session_module)
        if not name.startswith("_") and callable(getattr(session_module, name))
    }
    for name in public_callables:
        attr = getattr(session_module, name)
        # functools.lru_cache wrappers expose a `cache_info` attribute.
        assert not hasattr(attr, "cache_info"), (
            f"{name} appears to be lru_cache-wrapped; module-level caches were "
            "removed deliberately so callers can manage engine lifecycle"
        )
