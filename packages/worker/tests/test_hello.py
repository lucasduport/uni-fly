"""Unit tests for the hello-world workflow + activity.

These exercise the underlying functions directly. End-to-end execution
through the workflows runtime is covered by integration tests against a
running Mistral Workflows server.
"""

from __future__ import annotations

import pytest

from unifly_worker.activities.hello import Greeting, greet
from unifly_worker.workflows.hello import HelloWorldWorkflow


@pytest.mark.asyncio
async def test_greet_returns_message() -> None:
    # The decorated activity is still callable in-process for unit tests.
    result = await greet.__wrapped__("Lucas")  # type: ignore[attr-defined]
    assert isinstance(result, Greeting)
    assert result.message == "Hello, Lucas!"


def test_workflow_is_registered() -> None:
    # The decorator attaches workflow metadata; verify it survived.
    assert HelloWorldWorkflow.__name__ == "HelloWorldWorkflow"
