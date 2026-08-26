# A-share trading research

This private repository is the integration monorepo for the A-share trading
research platform. It establishes the migration boundary and target layout;
it is not the runtime source of truth during M0.

## M0 status

M0 foundation is in progress. This repository contains governance,
documentation, target-layout markers, and foundation checks only. Dashboard
and Niu Men source imports are deferred to the history-preserving import
phase. The existing Dashboard and Niu Men repositories remain independently
active and usable throughout the migration.

## Target layout

```text
a-share-trading-research/
├── apps/
│   └── dashboard/
├── packages/
│   ├── research-core/
│   └── niu-men-line-strategy/
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
