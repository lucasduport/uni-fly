# Companion database

SQLAlchemy 2.0 async models backing the worker's bookkeeping (sync state,
classification history, few-shot examples). Migrations live in `alembic/` at
the repo root and target Postgres 16.

Apply migrations against the local compose stack:

```bash
docker compose --profile migrate run --rm alembic
```

## Models

::: unifly_worker.db.models

## Session helpers

::: unifly_worker.db.session
