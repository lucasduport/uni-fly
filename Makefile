# Makefile — host-side dev commands for uni-fly.
#
# Loads .env so you only need to set COMPANION_DB_PASSWORD once; DATABASE_URL
# is composed from it on the fly. Containers (docker compose) build their own
# DATABASE_URL via compose interpolation — see docker-compose.yml.

ifneq (,$(wildcard .env))
include .env
export
endif

# Compose host-facing DATABASE_URL from COMPANION_DB_PASSWORD when not set
# explicitly. ?= preserves any DATABASE_URL the caller already exported.
DATABASE_URL ?= postgresql+asyncpg://companion:$(COMPANION_DB_PASSWORD)@localhost:5432/companion
export DATABASE_URL

.PHONY: help up down clean migrate test test-integration shell-db lint

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up:  ## Start the full local stack (companion-db, firefly, alembic, worker)
	docker compose up -d

down:  ## Stop the local stack (keeps DB volumes)
	docker compose down

clean:  ## Stop the local stack AND delete DB volumes (use after changing DB passwords)
	docker compose down -v

migrate:  ## Apply alembic migrations against the local companion-db
	uv run alembic upgrade head

test:  ## Run unit tests (skips integration)
	uv run pytest -m "not integration"

test-integration:  ## Run integration tests (requires companion-db running)
	uv run pytest -m integration

shell-db:  ## psql shell into the local companion-db
	docker compose exec companion-db psql -U companion -d companion

lint:  ## Ruff check
	uv run ruff check .
