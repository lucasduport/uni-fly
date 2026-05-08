# Getting started

## Prerequisites

- Python 3.12 (≤ 3.14)
- [uv](https://docs.astral.sh/uv/) ≥ 0.11

## Install

```bash
git clone https://github.com/lucasduport/uni-fly.git
cd uni-fly
uv sync --all-packages --all-groups --frozen
uv run pre-commit install                        # commit-stage hooks
uv run pre-commit install --hook-type pre-push   # push-stage hook (runs pytest)
cp .env.example .env
```

Fill `.env` with your `FIREFLY_TOKEN`, `MISTRAL_API_KEY`, and the workflow task queue.

## Run the worker

```bash
uv run unifly-worker
```

The worker connects to the Mistral Workflows runtime configured in your environment and
serves the `unifly-hello-world` workflow.

## Run the checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy packages/worker/src
uv run pytest
```

These are the same commands CI runs on every pull request to `main`.
