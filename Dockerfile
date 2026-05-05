# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /uvx /usr/local/bin/

WORKDIR /app

# Cache dependency resolution.
COPY pyproject.toml uv.lock ./
COPY packages/worker/pyproject.toml ./packages/worker/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --package unifly-worker

# Copy source and install the project itself.
COPY packages/worker/src ./packages/worker/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package unifly-worker

# ---------- Runtime ----------
FROM python:3.12-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app

ENTRYPOINT ["python", "-m", "unifly_worker"]
