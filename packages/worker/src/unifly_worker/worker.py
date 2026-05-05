"""Worker bootstrap for the Mistral Workflows runtime.

Workflows and activities are registered here. Keep this module thin: the
business logic lives in :mod:`unifly_worker.workflows` and
:mod:`unifly_worker.activities`.
"""

from __future__ import annotations

from mistralai import workflows
from mistralai.workflows.core.config.config import config as workflows_config
from mistralai.workflows.core.logging import LogLevel, setup_logging

from unifly_worker.config import Settings, get_settings
from unifly_worker.workflows import HelloWorldWorkflow

# All workflows the worker should serve. Add new entries as features land.
WORKFLOWS: list[type] = [HelloWorldWorkflow]


async def run(settings: Settings | None = None) -> None:
    """Connect to the Mistral Workflows runtime and serve workflows.

    Stays alive until cancelled (SIGINT/SIGTERM).
    """
    cfg = settings or get_settings()

    setup_logging(
        log_format=workflows_config.common.log_format,
        log_level=LogLevel(cfg.log_level.upper()),
        app_version=workflows_config.common.app_version,
    )

    await workflows.run_worker(WORKFLOWS)
