# Project layout

```
uni-fly/
├── .github/workflows/
│   ├── ci.yml              # lint, typecheck, tests
│   └── docs.yml            # build + deploy MkDocs to GitHub Pages
├── docs/                   # this site
├── packages/worker/        # unifly-worker package
├── scripts/
│   └── bump_cutoff.py      # roll the exclude-newer cutoff
├── pyproject.toml          # workspace root, all tool config
├── uv.lock                 # frozen resolution
├── mkdocs.yml              # docs site config
├── Dockerfile              # multi-stage worker image
└── README.md
```

## Where things live

| Concern                      | Location                                                |
| ---------------------------- | ------------------------------------------------------- |
| Workflow definitions         | `packages/worker/src/unifly_worker/workflows/`          |
| Activity implementations     | `packages/worker/src/unifly_worker/activities/`         |
| External clients (HTTP, SDKs)| `packages/worker/src/unifly_worker/clients/`            |
| Settings / config schema     | `packages/worker/src/unifly_worker/config.py`           |
| Tests                        | `packages/worker/tests/`                                |
| Docs                         | `docs/`                                                 |
| CI                           | `.github/workflows/`                                    |
