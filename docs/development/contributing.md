# Contributing

## Branching model

Two long-lived branches:

| Branch | Role                                            | Protection                              |
| ------ | ----------------------------------------------- | --------------------------------------- |
| `dev`  | Integration branch — every feature lands here   | PR + green CI required, no direct push  |
| `main` | Release branch — drives version tags + Pages    | PR + green CI + 1 review, no direct push|

```
feature/* ─PR→ dev ─(CI)─ merged
                    │
                    └─ when ready: PR dev → main → release-please tags + GitHub Release
```

## Workflow

1. Branch from `dev`: `git checkout dev && git pull && git checkout -b feat/<short-name>`.
2. Make changes; pre-commit formats and lints on commit.
3. Run the local checks (see [Getting started](../getting-started.md)).
4. Open a PR **against `dev`**. CI runs lint, type check, tests (Python 3.12 + 3.13), and
   pre-commit.
5. Once merged into `dev`, accumulated changes ship to production by opening a PR from
   `dev` → `main`. Merging that PR triggers
   [release-please](https://github.com/googleapis/release-please) to bump the version
   and cut a GitHub Release.

## Commit messages — Conventional Commits

release-please reads the commit history on `main` to compute the next version. Use
[Conventional Commits](https://www.conventionalcommits.org/):

- `feat: …` → minor bump (or patch while < 1.0).
- `fix: …` → patch bump.
- `feat!: …` or `BREAKING CHANGE:` footer → major bump (or minor while < 1.0).
- `chore:`, `docs:`, `refactor:`, `test:`, `ci:` → no version bump, but appear in the changelog.

PR titles are squash-merged into `dev` and become individual commits on `main` when the
release PR merges, so write PR titles as conventional commits too.

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
