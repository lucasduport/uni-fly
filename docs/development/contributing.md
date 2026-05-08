# Contributing

## Branching model

Single long-lived branch:

| Branch | Role                                          | Protection                              |
| ------ | --------------------------------------------- | --------------------------------------- |
| `main` | Release branch — drives version tags + Pages  | PR + green CI + 1 review, no direct push |

```
feature/* ─PR→ main ─(CI)─ merged → release-please auto-bumps version & tags
```

## Workflow

1. Branch from `main`: `git checkout main && git pull && git checkout -b feat/<short-name>`.
2. Make changes; pre-commit formats and lints on commit.
3. Run the local checks (see [Getting started](../getting-started.md)).
4. Open a PR **against `main`**. CI runs lint, type check, tests (Python 3.12 + 3.13), and
   pre-commit.
5. Once merged into `main`:
   - If your PR includes conventional commit messages that warrant a version bump
     (see below), [release-please](https://github.com/googleapis/release-please) 
     automatically opens a **release PR** to `main` with the version bump and changelog.
   - Merge the release PR to publish a GitHub Release with the new version tag.

## Commit messages — Conventional Commits

release-please reads the commit history on `main` to compute the next version. Use
[Conventional Commits](https://www.conventionalcommits.org/):

- `feat: …` → minor bump (or patch while < 1.0).
- `fix: …` → patch bump.
- `feat!: …` or `BREAKING CHANGE:` footer → major bump (or minor while < 1.0).
- `chore:`, `docs:`, `refactor:`, `test:`, `ci:` → no version bump, but appear in the changelog.

PR titles are squash-merged and become individual commits on `main`, so write PR titles
as conventional commits too.

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
