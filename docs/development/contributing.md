# Contributing

## Workflow

1. Branch from `main`: `git checkout -b feat/<short-name>`.
2. Make changes; pre-commit will format and lint on commit.
3. Run the local checks (see [Getting started](../getting-started.md)).
4. Open a PR. CI runs lint, type check, tests (Python 3.12 + 3.13), and pre-commit.

## Coding style

- Ruff handles formatting and linting (see `[tool.ruff]` in `pyproject.toml`).
- Mypy is strict — every function needs annotations.
- Tests use pytest with `asyncio_mode = "auto"`.

## Dependency hygiene

`pyproject.toml` pins `[tool.uv].exclude-newer` to (today − 7 days) so the resolver
ignores packages that were just published. Roll it forward when you intentionally want
newer releases:

```bash
uv run python scripts/bump_cutoff.py
uv lock
```

CI uses `uv sync --frozen`; never commit a regenerated lockfile without bumping the
cutoff first.

## Adding a workflow

1. Define a class in `packages/worker/src/unifly_worker/workflows/<name>.py` using
   `@workflows.workflow.define(...)`.
2. Define activities in `packages/worker/src/unifly_worker/activities/<name>.py` using
   `@workflows.activity()`.
3. Register the workflow in `worker.py` (`WORKFLOWS` list).
4. Add unit tests under `packages/worker/tests/`.
