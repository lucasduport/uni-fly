# uni-fly

Firefly III companion — a [Mistral Workflows](https://docs.mistral.ai/studio-api/workflows/)
worker that fetches bank transactions, classifies them with Mistral AI, and pushes them to a
Firefly III instance via its REST API.

## What's here

- A single Python worker process that hosts workflows and activities.
- Pluggable bank providers (CIC, SG, Boursorama, Swile — coming soon).
- Mistral-powered classification + tag suggestions.
- A typed Firefly III HTTP client.

## Where to next

- [Getting started](getting-started.md) — install the toolchain and run the worker locally.
- [Architecture](architecture.md) — how the pieces fit together.
- [Contributing](development/contributing.md) — workflow, conventions, CI.
- [API reference](reference/worker.md) — generated from docstrings.

!!! info "Status"
    Project is in early scaffolding. Only the hello-world workflow is implemented today;
    bank sync and classification activities land in the upcoming phases.
