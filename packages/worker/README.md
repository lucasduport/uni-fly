# unifly-worker

Temporal worker for the Firefly III companion. Hosts workflows and activities that:

1. Fetch transactions from configured bank providers.
2. Classify them via Mistral AI.
3. Push them to Firefly III through its REST API.

## Run locally

```bash
uv sync
uv run unifly-worker
```

Configuration is loaded from environment variables (see `.env.example` at the repo root).
