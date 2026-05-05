"""Hello-world workflow used to validate the worker plumbing."""

from __future__ import annotations

from mistralai import workflows

from unifly_worker.activities.hello import Greeting, greet


@workflows.workflow.define(
    name="unifly-hello-world",
    workflow_display_name="Hello World",
    workflow_description="Smoke-test workflow for the unifly worker.",
)
class HelloWorldWorkflow:
    """Calls :func:`greet` once and returns the greeting."""

    @workflows.workflow.entrypoint
    async def run(self, name: str) -> Greeting:
        return await greet(name)
