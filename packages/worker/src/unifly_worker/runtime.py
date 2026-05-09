"""Process-wide runtime container.

The runtime owns long-lived dependencies (DB engine, sessionmaker, HTTP
clients) so individual workflows / activities receive ready-to-use handles
instead of pulling them from module-level singletons. Lifecycle is explicit:
``async with WorkerRuntime.from_settings(s) as rt: ...``.

Opinionated defaults (pool sizing, timeouts) live here — at the edge — not
in the reusable ``db.session`` / ``clients.firefly`` primitives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from unifly_worker.config import Settings
from unifly_worker.db.session import create_engine, make_sessionmaker

logger = logging.getLogger(__name__)

# Engine pool sizing chosen for a worker that fans out activities concurrently.
# Tune via WorkerRuntime.from_settings(..., pool_size=..., max_overflow=...).
DEFAULT_DB_POOL_SIZE = 5
DEFAULT_DB_MAX_OVERFLOW = 5


@dataclass(frozen=True, slots=True)
class WorkerRuntime:
    """Bundle of long-lived dependencies for activities.

    Construct via :meth:`from_settings`; never instantiate directly so the
    creation path stays a single, audited code path.
    """

    settings: Settings
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        pool_size: int = DEFAULT_DB_POOL_SIZE,
        max_overflow: int = DEFAULT_DB_MAX_OVERFLOW,
    ) -> Self:
        """Build a runtime from :class:`Settings` and engine sizing knobs."""
        logger.info(
            "Initialising worker runtime db_host=%s pool_size=%d max_overflow=%d",
            _db_host(settings.database_url),
            pool_size,
            max_overflow,
        )
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            future=True,
        )
        return cls(
            settings=settings,
            engine=engine,
            sessionmaker=make_sessionmaker(engine),
        )

    async def aclose(self) -> None:
        """Dispose of the underlying engine, closing all pool connections."""
        logger.info("Disposing worker runtime engine")
        await self.engine.dispose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


def _db_host(url: str) -> str:
    return url.rsplit("@", 1)[-1]
