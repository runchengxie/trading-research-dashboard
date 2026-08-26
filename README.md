# A-share trading research

This private repository is the integration monorepo for the A-share trading
research platform. Dashboard M1 is imported here, but the monorepo is not yet
the runtime source of truth.

## M1 status

The Dashboard application is imported under `apps/dashboard/` with its
history-preserving boundary recorded in the
[Dashboard import manifest](docs/migration/dashboard-import.md). The existing
Dashboard repository remains the active runtime source while migration work is
reviewed. Niu Men remains the next separate history-preserving import; its
source and strategy logic are not included here.

## Target layout

```text
a-share-trading-research/
├── apps/
│   └── dashboard/
├── packages/
│   ├── research-core/
│   └── niu-men-line-strategy/
├── schemas/
├── docs/
│   └── migration/
├── scripts/
├── tests/
├── pyproject.toml
└── README.md
```

`research-workspace`, `market-data-platform`, and `etf-minute-fetcher` remain
external infrastructure. See [the migration guide](docs/migration/README.md)
for the phased plan and [source commit record](docs/migration/source-commits.md)
for the first import rollback points.
