# uni-fly

Firefly III companion — a Temporal-driven worker that fetches bank transactions, classifies
them with Mistral AI, and pushes them to a Firefly III instance via its REST API.

## Layout

```
uni-fly/
├── pyproject.toml              # uv workspace root
├── packages/
│   └── worker/                 # unifly-worker — Temporal worker (workflows + activities)
│       ├── pyproject.toml
│       ├── src/unifly_worker/
│       └── tests/
├── .github/workflows/ci.yml    # lint, typecheck, test
├── Dockerfile                  # worker image
└── Makefile                    # common dev commands
```

The repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/).
Future packages (e.g. shared clients, classifier libs) live alongside `worker/` under `packages/`.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) ≥ 0.11

## Getting started

```bash
uv sync --all-packages --all-groups --frozen   # install from lockfile
uv run pre-commit install                      # one-time hook setup
cp .env.example .env                           # fill in FIREFLY_TOKEN, MISTRAL_API_KEY, ...
```

Run the worker locally:

```bash
uv run unifly-worker
```

## Common commands

| Command                                          | Action                                   |
| ------------------------------------------------ | ---------------------------------------- |
| `uv sync --all-packages --all-groups --frozen`   | Install from lockfile (reproducible)     |
| `uv lock`                                        | Re-resolve `uv.lock` after dep changes   |
| `uv run ruff check .`                            | Lint                                     |
| `uv run ruff format .`                           | Format                                   |
| `uv run mypy packages/worker/src`                | Type check                               |
| `uv run pytest`                                  | Tests with coverage                      |
| `uv run pre-commit run --all-files`              | Run all pre-commit hooks                 |
| `uv run python scripts/bump_cutoff.py && uv lock`| Roll the supply-chain cutoff +7d         |

## Supply-chain hygiene

`pyproject.toml` pins `[tool.uv].exclude-newer` to (today − 7 days). The resolver
will refuse packages published after that date, giving the wider community time to
flag a malicious release before it lands in our lockfile. Bump it with the script
above when you're ready to pull in newer deps.

## CI

GitHub Actions runs lint, type check, and tests on every push and PR — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## License

MIT
