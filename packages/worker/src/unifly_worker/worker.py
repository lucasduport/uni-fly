"""Worker bootstrap for the Mistral Workflows runtime.

Workflows and activities are registered here. Keep this module thin: business
logic lives in :mod:`unifly_worker.workflows` and
:mod:`unifly_worker.activities`. The bootstrap also owns construction of the
process-wide :class:`WorkerRuntime`, the only place where engine sizing and
other infrastructural opinions are wired in.
"""

from __future__ import annotations

import logging

from mistralai import workflows
from mistralai.workflows.core.config.config import config as workflows_config
from mistralai.workflows.core.logging import LogLevel, setup_logging

from unifly_worker.config import Settings, get_settings
from unifly_worker.runtime import WorkerRuntime
from unifly_worker.workflows import HelloWorldWorkflow

logger = logging.getLogger(__name__)

# All workflows the worker should serve. Add new entries as features land.
WORKFLOWS: list[type[HelloWorldWorkflow]] = [HelloWorldWorkflow]


async def run(settings: Settings | None = None) -> None:
    """Connect to the Mistral Workflows runtime and serve workflows.

    Stays alive until cancelled (SIGINT/SIGTERM). The :class:`WorkerRuntime`
    is built and torn down with the worker process — activities receive it
    via the runtime registration mechanism in Phase 2.
    """
    cfg = settings or get_settings()

    setup_logging(
        log_format=workflows_config.common.log_format,
        log_level=LogLevel(cfg.log_level.upper()),
        app_version=workflows_config.common.app_version,
    )

    # The Mistral Workflows SDK validates DEPLOYMENT_NAME itself at run_worker
    # time; surface a clearer message in our log to make local misconfig obvious.
    deployment_name = workflows_config.worker.deployment_name
    if not deployment_name:
        logger.warning(
            "DEPLOYMENT_NAME is not set; Mistral Workflows will refuse to start. "
            "Set DEPLOYMENT_NAME to a stable identifier (e.g. 'unifly-worker')."
        )
    logger.info("Starting unifly-worker deployment_name=%s", deployment_name or "<unset>")

    async with WorkerRuntime.from_settings(cfg):
        await workflows.run_worker(WORKFLOWS)
