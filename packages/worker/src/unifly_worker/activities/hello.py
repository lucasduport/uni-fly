"""Hello-world activity used to validate the worker plumbing."""

from __future__ import annotations

import logging

import pydantic
from mistralai import workflows

logger = logging.getLogger(__name__)


class Greeting(pydantic.BaseModel):
    """Result of a :func:`greet` invocation."""

    message: str


@workflows.activity()
async def greet(name: str) -> Greeting:
    """Return a greeting for ``name``.

    Trivial by design — the goal is to prove the workflow → activity wiring.
    """
    async with workflows.task("activity.greet", {"name": name}):
        logger.debug("Greeting name=%s", name)
        return Greeting(message=f"Hello, {name}!")
