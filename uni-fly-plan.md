# Plan: Firefly Companion — Mistral Workflows Worker

## Context

Build a worker (Mistral Workflows runtime) that fetches bank transactions, classifies them with Mistral AI, and pushes them to Firefly III via its REST API. No forking, no companion API server — just a worker process that plugs into Firefly III with an API URL + Personal Access Token.

> Historical note: earlier drafts of this plan referenced Temporal. The actual
> implementation uses [`mistralai-workflows`](https://github.com/mistralai/mistralai-workflows)
> — the workflow shape (workflows + activities + scheduling) is the same,
> only the SDK / runtime differ.

---

## Architecture

```
                          Temporal Server
                                │
                     ┌──────────┴──────────┐
                     │  Temporal Schedules  │
                     │  (bank sync, classify│
                     │   every 6h, Fri 22h) │
                     └──────────┬──────────┘
                                │
┌──────────────────────────────┼──────────────────────────────┐
│              firefly-companion (Temporal Worker)             │
│                              │                              │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────────┐     │
│  │ bank_sync│─►│  classifier  │─►│  firefly_client    │─────┼──► Firefly III API
│  │  (woob)  │  │ (mistral ai) │  │  (httpx)           │     │    (URL + PAT)
│  └──────────┘  └─────────────┘  └────────────────────┘     │
│                                                             │
└─────────────────────────────┬───────────────────────────────────┘
                          │
                    Companion DB (PostgreSQL)
                    (sync state, classification history, examples)
```

One process, three modules:

1. **bank_sync** — Fetches transactions from CIC, SG, Boursorama via woob, Swile via custom HTTP client
2. **classifier** — Categorizes expenses via Mistral AI (mistralai SDK) with structured outputs
3. **firefly_client** — Typed httpx wrapper around Firefly III v1 API. Configured with `FIREFLY_URL` + `FIREFLY_TOKEN` (Personal Access Token)

---

## Firefly III Integration

The worker only needs two env vars to plug into any Firefly III instance:

```bash
FIREFLY_URL=https://firefly.example.com
FIREFLY_TOKEN=eyJ...  # Personal Access Token from Firefly III UI
```

### Key API endpoints used (verified in routes/api.php):

| Operation | Endpoint |
|-----------|----------|
| Create transaction | `POST /api/v1/transactions` (with external_id for dedup) |
| Update transaction | `PUT /api/v1/transactions/{id}` (set category, tags) |
| Search uncategorized | `GET /api/v1/search/transactions?query=has_no_category` |
| Manage categories | `POST/GET /api/v1/categories` |
| Manage tags | `POST/GET /api/v1/tags` |
| Create rules | `POST /api/v1/rules` (auto-categorization rules) |

---

## Temporal Workflows

### BankSyncAndClassifyWorkflow (main workflow)

A single workflow that does the full pipeline: fetch -> classify -> push. Runs on a Temporal Schedule (configurable: every 6h default, Friday 22:00 for batch reclassification).

```
Schedule triggers workflow
  │
  ├─ Activity: fetch_bank_accounts        (read config from DB)
  │
  ├─ Activity: sync_bank (per account)    (woob fetches new transactions)
  │     ├─ parallel across accounts
  │     └─ returns raw transactions
  │
  ├─ Activity: dedup_transactions         (check sync_log, skip known external_ids)
  │
  ├─ Activity: classify_batch             (Mistral AI structured output)
  │     ├─ loads few-shot examples from DB
  │     └─ returns {category, tags, confidence} per transaction
  │
  ├─ Activity: push_to_firefly            (POST /api/v1/transactions with category + tags)
  │
  └─ Activity: record_sync_state          (update sync_log + classifications table)
```

### RuleGenerationWorkflow (weekly, Sunday 10:00)

Analyzes classification history. When a merchant->category mapping is consistent (5+ times), creates a Firefly III rule via `POST /api/v1/rules` so future transactions are auto-categorized by Firefly III itself — no LLM needed.

### Configuration

Schedules are registered at worker startup and can be updated via Temporal UI or tctl:

```python
# Registered at startup
schedules = {
    "bank-sync": IntervalSpec(every=timedelta(hours=6)),
    "friday-reclassify": CalendarSpec(day_of_week="FRIDAY", hour=22, minute=0),
    "rule-generation": CalendarSpec(day_of_week="SUNDAY", hour=10, minute=0),
}
```

Users can pause, trigger manually, or change intervals via Temporal UI at localhost:8233.

---

## Companion DB Schema (PostgreSQL)

### Bank account configuration

```sql
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,           -- 'cic', 'sg', 'boursorama', 'swile'
    account_type TEXT NOT NULL,       -- 'checking', 'pea', 'meal_voucher', 'transport'
    credentials_enc BYTEA NOT NULL,   -- encrypted woob backend config
    firefly_account_id INT,           -- mapped Firefly III account ID
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Dedup state (prevents re-importing the same transaction)

```sql
CREATE TABLE sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID REFERENCES bank_accounts(id),
    external_id TEXT NOT NULL UNIQUE,
    firefly_transaction_id INT,
    synced_at TIMESTAMPTZ DEFAULT now()
);
```

### LLM classification history

```sql
CREATE TABLE classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firefly_transaction_id INT NOT NULL,
    description TEXT,
    assigned_category TEXT,
    assigned_tags TEXT[],
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Few-shot examples for classification prompt

```sql
CREATE TABLE classification_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    amount NUMERIC,
    source_account TEXT,
    correct_category TEXT NOT NULL,
    correct_tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12+ |
| Workflow engine | Mistral Workflows (`mistralai-workflows` SDK) |
| LLM | Mistral AI (mistralai SDK, structured outputs) |
| Bank scraping | woob (CIC, SG, Boursorama) |
| Firefly III client | httpx |
| DB | PostgreSQL 16, SQLAlchemy 2.0, Alembic |

---

## Docker Compose (Local Dev)

> Phase 1 ships a slimmed-down compose stack: `firefly`, `firefly-db`,
> `companion-db`, `companion-worker`, and a one-shot `alembic` service. The
> Mistral Workflows runtime itself is not included — point the worker at
> whichever runtime endpoint you use (cloud or self-hosted).

```yaml
services:
  # --- Firefly III ---
  firefly:
    image: fireflyiii/core:latest
    environment:
      DB_CONNECTION: pgsql
      DB_HOST: firefly-db
      DB_DATABASE: firefly
      DB_USERNAME: firefly
      DB_PASSWORD: secret
      APP_KEY: ${FIREFLY_APP_KEY}
    ports: ["8080:8080"]
    depends_on: [firefly-db]

  firefly-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: firefly
      POSTGRES_USER: firefly
      POSTGRES_PASSWORD: secret
    volumes: [firefly-pgdata:/var/lib/postgresql/data]

  # --- Temporal ---
  temporal:
    image: temporalio/auto-setup:latest
    environment:
      DB: postgresql
      DB_PORT: 5432
      POSTGRES_USER: temporal
      POSTGRES_PWD: secret
      POSTGRES_SEEDS: temporal-db
    ports: ["7233:7233"]
    depends_on: [temporal-db]

  temporal-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: temporal
      POSTGRES_USER: temporal
      POSTGRES_PASSWORD: secret
    volumes: [temporal-pgdata:/var/lib/postgresql/data]

  temporal-ui:
    image: temporalio/ui:latest
    environment:
      TEMPORAL_ADDRESS: temporal:7233
    ports: ["8233:8080"]
    depends_on: [temporal]

  # --- Companion Worker ---
  companion-worker:
    build: .
    command: python -m firefly_companion.worker
    environment:
      DATABASE_URL: postgresql+asyncpg://companion:secret@companion-db/companion
      FIREFLY_URL: http://firefly:8080
      FIREFLY_TOKEN: ${FIREFLY_TOKEN}
      TEMPORAL_ADDRESS: temporal:7233
      MISTRAL_API_KEY: ${MISTRAL_API_KEY}
    depends_on: [companion-db, temporal]

  companion-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: companion
      POSTGRES_USER: companion
      POSTGRES_PASSWORD: secret
    volumes: [companion-pgdata:/var/lib/postgresql/data]

volumes:
  firefly-pgdata:
  companion-pgdata:
  temporal-pgdata:
```

8 containers. No Redis. Secrets via .env file locally, K8s Secrets in prod.

---

## Project Structure

```
firefly-companion/
├── firefly_companion/
│   ├── __init__.py
│   ├── worker.py              # Temporal worker entrypoint (registers workflows + activities)
│   ├── workflows/
│   │   ├── bank_sync.py       # BankSyncAndClassifyWorkflow
│   │   └── rule_generation.py # RuleGenerationWorkflow
│   ├── activities/
│   │   ├── bank_fetch.py      # woob activities per provider
│   │   ├── classify.py        # Mistral AI classification activity
│   │   ├── firefly_push.py    # POST/PUT to Firefly III
│   │   ├── dedup.py           # sync_log checks
│   │   └── rules.py           # auto-rule creation
│   ├── clients/
│   │   ├── firefly.py         # httpx Firefly III API wrapper
│   │   ├── mistral.py         # Mistral AI client wrapper
│   │   └── swile.py           # Swile HTTP client
│   ├── models.py              # SQLAlchemy models
│   └── config.py              # Settings (pydantic-settings)
├── alembic/                   # DB migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## K8s Deployment

- **Temporal**: Deploy via temporalio/helm-charts or use Temporal Cloud
- **Companion Worker**: Single Deployment (can scale replicas — Temporal distributes tasks safely)
- **Databases**: Managed PostgreSQL in prod
- **Secrets**: `MISTRAL_API_KEY`, `FIREFLY_TOKEN`, DB credentials via K8s Secrets / Vault
- **Config**: Schedules and bank accounts configurable without redeployment (via DB + Temporal UI)

---

## Phased Implementation

### Phase 1: Skeleton + Firefly Client (week 1)

- Project scaffold (pyproject.toml, Docker Compose, Alembic)
- firefly_client module — create/read/update transactions, categories, tags
- Temporal worker with hello-world workflow to validate connectivity
- Alembic migrations for companion DB schema

### Phase 2: Bank Sync — CIC first (week 2-3)

- woob integration for CIC
- BankSyncAndClassifyWorkflow (without classification — just fetch + push)
- Dedup via external_id in sync_log
- Temporal Schedule for periodic sync

### Phase 3: Mistral Classification (week 4-5)

- Mistral AI structured output for French expense categorization
- Add classify_batch activity to the workflow (fetch -> classify -> push)
- Classification history tracking
- Seed classification_examples with initial category definitions

### Phase 4: Remaining Banks + Rules (week 6-7)

- SG, Boursorama (bank + PEA), Swile providers
- RuleGenerationWorkflow — auto-creates Firefly III rules from consistent patterns

### Phase 5: Hardening + K8s (week 8)

- Activity retry policies, timeouts, heartbeats
- Structured logging, Prometheus metrics
- Helm chart
- Bank credential encryption at rest

---

## Verification

1. **Phase 1**: firefly_client can CRUD transactions/categories/tags against local Firefly III
2. **Phase 2**: Trigger BankSyncAndClassifyWorkflow manually in Temporal UI, confirm CIC transactions appear in Firefly III with correct external_id
3. **Phase 3**: Run workflow with classification enabled, confirm transactions land in Firefly III with categories and tags set
4. **Phase 4**: Verify all bank providers sync correctly. Trigger RuleGenerationWorkflow, confirm rules appear in Firefly III
5. **E2E**: Full scheduled flow — bank sync -> classify -> push -> rules generated -> next sync transactions auto-categorized by Firefly III rules
