#!/usr/bin/env python3
"""Roll ``[tool.uv].exclude-newer`` to (today - 7 days).

Run via ``make bump-cutoff``. The 7-day window is a supply-chain hygiene
guard: it lets the broader ecosystem flag a malicious release before our
resolver is allowed to pull it in.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
PATTERN = re.compile(r'exclude-newer = "[^"]+"')
WINDOW_DAYS = 7


def main() -> int:
    cutoff = (datetime.now(UTC) - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, count = PATTERN.subn(f'exclude-newer = "{cutoff}"', text)
    if count == 0:
        print("error: exclude-newer key not found in pyproject.toml", file=sys.stderr)
        return 1
    if new_text == text:
        print(f"exclude-newer already set to {cutoff}")
        return 0
    PYPROJECT.write_text(new_text, encoding="utf-8")
    print(f"exclude-newer = {cutoff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
