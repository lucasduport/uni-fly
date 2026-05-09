"""Smoke tests: import surface and version are stable."""

from __future__ import annotations

import unifly_worker
from unifly_worker.config import Settings


def test_package_exposes_version() -> None:
    assert isinstance(unifly_worker.__version__, str)
    assert unifly_worker.__version__.count(".") >= 2


def test_settings_defaults_are_sane(settings: Settings) -> None:
    assert settings.firefly_url.startswith("http")
    assert settings.firefly_token == "test-token"
