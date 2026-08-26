# A-Share Trading Research Monorepo Design

## Status

Approved design for the initial monorepo foundation. This document describes
the repository boundary and migration sequence; it does not yet move source
code from the existing repositories.

## Goal

Create a private integration repository for the A-share trading research
platform while preserving the standalone usability of `wu-t0-trading-dashboard`
and `niu-men-line-strategy` throughout the migration.

## Context

The two existing repositories have converged at their public boundary:

- Dashboard consumes a versioned `niu_men.research_snapshot.v2` JSON artifact.
- Niu Men owns research execution, OOS computation, provenance, schema
  validation, and snapshot publication.
- Dashboard owns market views, frontend rendering, graceful research fallback,
  and the consumer-side contract checks.
- Market data and minute-data fetchers remain external infrastructure consumed
  through stable file/data contracts.

The previous contract and publication work was intentionally completed in the
two existing repositories. The monorepo is therefore a new integration layer,
not a replacement that changes both projects in one operation.

## Repository boundary

The new repository is private because both source repositories are private and
Niu Men contains research-boundary material. `research-workspace` is not part
of this repository, and market-data infrastructure is not copied into it.

```text
a-share-trading-research/
├── apps/
│   └── dashboard/
├── packages/
│   ├── research-core/
│   └── niu-men-line-strategy/
├── schemas/
├── docs/
├── scripts/
├── pyproject.toml
└── README.md
```

The intended dependency direction is:

```text
market-data-platform / etf-minute-fetcher
                 │ stable data contracts
                 ▼
          research-core
            │       │
            ▼       ▼
      Niu Men     Dashboard
      producer    consumer
```

`research-core` contains language-neutral contract assets and small shared
validation/provenance utilities. It must not contain Niu Men indicators,
signals, backtest rules, or Dashboard presentation code.

## Migration strategy

### Phase M0: foundation

Create the private repository, root README, contribution guidance, directory
layout, and a minimal CI workflow. The foundation PR must not modify either
source repository and must not claim that the monorepo is already the runtime
source of truth.

### Phase M1: history-preserving imports

Import the existing repositories into their new subdirectories while retaining
their commit history where practical:

- `wu-t0-trading-dashboard` becomes `apps/dashboard/`.
- `niu-men-line-strategy` becomes `packages/niu-men-line-strategy/`.

The initial import may keep compatibility entry points and the existing
internal layouts. It must not silently rewrite strategy logic or change the
snapshot wire contract. A migration note records the source commit for each
import and the source repository URLs.

The original repositories remain active during this phase. Changes are not
automatically mirrored in both directions; the monorepo becomes authoritative
only after a later cutover decision.

### Phase M2: shared contract extraction

Move the canonical snapshot schema, contract fixtures, and provenance rules to
`packages/research-core` plus the root `schemas/` compatibility location.

The required invariants are:

- Wire version remains `niu_men.research_snapshot.v2`.
- Niu Men remains the producer and schema owner until the extraction is
  verified.
- Dashboard continues to treat research as optional.
- Missing or incomplete provenance remains explicit and produces a warning.
- Dashboard does not import Niu Men implementation modules.

This phase should introduce package-level tests before removing duplicated
copies. The old repositories keep compatibility copies until the monorepo
consumer and producer tests pass against the shared package.

### Phase M3: Python package and runtime convergence

Package the Dashboard Python code under the monorepo application boundary and
unify Python to 3.11 or newer. Use a uv workspace or equivalent explicit local
package dependencies rather than `sys.path` imports.

The target relationship is:

```text
apps/dashboard  ->  packages/research-core
packages/niu-men-line-strategy  ->  packages/research-core
```

Compatibility CLI wrappers may remain temporarily, but new code must import
from package paths. This phase is separate from the foundation and history
imports so Python-version and dependency failures cannot be confused with
repository migration failures.

### Phase M4: CI and release cutover

Add monorepo path-aware CI and a release workflow that can:

1. validate research-core contracts;
2. run Niu Men producer tests and snapshot validation;
3. run Dashboard Python/Web tests and build checks;
4. publish a reviewable Dashboard snapshot update;
5. retain external market-data inputs and credentials outside Git history.

Only after one or more successful release cycles should the original
repositories be considered compatibility mirrors or archived. That decision
requires a separate review and is not part of this foundation.

## Data and artifact policy

Raw market data, full OOS CSV files, credentials, and external data-platform
directories are not committed to the monorepo. The repository stores schemas,
fixtures, manifests, generated snapshots, and reproducibility metadata that do
not expose local absolute paths or restricted source material.

The existing Parquet and manifest contracts remain the integration boundary to
market-data infrastructure. A later research-run workflow may upload or pass
external artifacts to the publisher, but the foundation must not assume that a
GitHub runner can access a developer's local `DATA_PLATFORM_ROOT`.

## Compatibility and rollback

Every migration phase produces a separately reviewable PR. Until cutover:

- Existing repositories continue to build and test independently.
- Existing Dashboard deployment remains sourced from its own repository.
- Existing Niu Men publication remains sourced from its own repository.
- No git submodules are introduced.
- No destructive deletion or repository archival is performed.

If a phase fails, the PR can be closed and the original repositories continue
to operate from their last known-good `main` commits.

## Initial success criteria

The foundation phase is complete when:

1. The private repository has a documented target layout.
2. The repository explicitly excludes research-workspace and market-data
   infrastructure from its ownership boundary.
3. A root CI check validates the repository structure and Markdown/spec files.
4. The migration plan identifies source commits and a rollback point for each
   imported project.
5. No source implementation has been copied or changed yet.

## Non-goals

The foundation does not:

- merge Dashboard and Niu Men into one Python package;
- change Niu Men strategy logic or research results;
- rewrite the Dashboard UI;
- alter `research_snapshot.v2`;
- migrate `research-workspace`;
- move market-data storage or fetchers;
- archive or delete either original repository;
- guarantee that the monorepo is ready for production deployment.
