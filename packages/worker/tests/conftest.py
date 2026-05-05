"""Shared pytest fixtures for the worker test suite."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from unifly_worker.config import Settings, get_settings


@pytest.fixture
def settings() -> Iterator[Settings]:
    """Provide a fresh, isolated Settings instance per test."""
    get_settings.cache_clear()
    yield Settings(
        workflow_task_queue="test-queue",
        firefly_url="http://localhost:8080",
        firefly_token="test-token",
        mistral_api_key="test-key",
    )
    get_settings.cache_clear()
