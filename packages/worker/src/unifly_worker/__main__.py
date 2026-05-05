"""CLI entrypoint: ``python -m unifly_worker`` or ``unifly-worker``."""

from __future__ import annotations

import asyncio

from unifly_worker.worker import run


def main() -> None:
    """Synchronous wrapper used by the console script."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
