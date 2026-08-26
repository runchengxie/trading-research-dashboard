# M1 History-Preserving Imports Design

## Status

Design approved for implementation planning on 2026-08-26. This document
defines the first source-code migration phase for the private
`a-share-trading-research` integration monorepo.

## Goal

Import the current Dashboard and Niu Men implementations into their approved
monorepo destinations while preserving useful Git history and keeping raw
market data, generated research outputs, credentials, and restricted source
material outside the monorepo history.

M1 produces two independently reviewable pull requests:

1. Dashboard into `apps/dashboard/`.
2. Niu Men into `packages/niu-men-line-strategy/`.

The existing source repositories remain active and unchanged during M1.

## Boundaries

The following remain external and are not imported:

- `research-workspace`
- `market-data-platform`
- `etf-minute-fetcher`

M1 does not extract `research-core`, change Python version requirements, make
the root project the runtime source of truth, or change the Niu Men strategy
logic. Those are M2/M3 concerns.

## Source snapshots

The imports use these exact source commits, recorded in
`docs/migration/source-commits.md`:

| Source | Commit | Destination |
| --- | --- | --- |
| `wu-t0-trading-dashboard` | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` | `apps/dashboard/` |
| `niu-men-line-strategy` | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` | `packages/niu-men-line-strategy/` |

The import records must identify the source repository, exact source commit,
destination prefix, path filters, and excluded paths so a reviewer can
reproduce the result.

## Import method

Each source is imported in an isolated temporary clone or worktree:

1. Start from the exact source commit.
2. Rewrite only the selected source paths into the destination prefix with a
   history-aware path filter.
3. Remove prohibited paths from the rewritten history, not merely from the
   final checkout.
4. Merge the filtered history into the migration branch with unrelated
   histories allowed.
5. Remove temporary remotes and verify that the monorepo contains no
   submodules or gitlinks.

The final monorepo history must not contain excluded files introduced by the
M1 import. A current-tree deletion alone is insufficient because the purpose
of the filter is to prevent protected material from entering Git history.

## Dashboard import contract

The Dashboard import may include the following paths, rewritten below
`apps/dashboard/`:

- `src/`
- `web/`, except generated `web/public/data.json` and
  `web/public/research.json`
- `backtest/`
- `tests/`
- `scripts/`
- `docs/backtest.md`, `cloudflare-workers.md`, `configuration.md`,
  `data-sources.md`, `indicators.md`, `outputs.md`,
  `research-snapshot.md`, `troubleshooting.md`, and `web-frontend.md`
- `schemas/research-snapshot.schema.json`
- `pyproject.toml`, `uv.lock`, `wrangler.jsonc`, `README.md`, and `.gitignore`

The import must exclude:

- `data/raw/`
- generated web data and research snapshots
- `.env*` and other credentials
- local environment files and caches
- legacy root scripts when their maintained equivalents already exist under
  `src/`
- source-repository CI files that would execute independently from the
  monorepo root

The Dashboard application behavior, current selected instrument, research
freshness handling, and `research_snapshot.v2` consumer behavior are not
changed by this import.

## Niu Men import contract

The Niu Men import may include the following paths, rewritten below
`packages/niu-men-line-strategy/`:

- `src/`
- `scripts/`
- `tests/`
- `schemas/research-snapshot.schema.json`
- `README.md`, `pyproject.toml`, and `.gitignore`
- `docs/README.md`, `a1-integration.md`, `dashboard-snapshot.md`,
  `data-contract.md`, `maintenance-and-quality.md`,
  `oos-stability-diagnostics.md`, `restricted-strategy-notes.md`,
  `portfolio-backtester-adapter.md`, and `strategy-spec.md`

The import must exclude:

- `artifacts/`
- OOS CSV/JSON results and generated research outputs
- `docs/original-transcript.md`
- research findings and portfolio-result documents that are outputs rather
  than implementation or contract documentation
- `.env*`, local data, caches, and source-repository CI files

The `niu_men.research_snapshot.v2` wire version, existing provenance fields,
quality-warning semantics, and strategy logic remain unchanged.

## Monorepo integration

After each filtered history import:

- replace the corresponding M0 layout marker README with an accurate package
  boundary document;
- update `docs/migration/source-commits.md` with the imported commit and
  filtering manifest;
- update the M0 foundation checker and tests so the new tracked paths are
  explicitly allowed and prohibited paths remain rejected;
- keep root dependency metadata and CI behavior unchanged except for the
  minimum path-aware changes needed to validate the imported package;
- do not add a git submodule or source-repository remote to the committed
  repository configuration.

The root `pyproject.toml` is not converted into a workspace in M1. Nested
source metadata may remain as compatibility documentation until the separate
M3 package-convergence migration.

## Verification and acceptance criteria

Each PR must provide:

1. A clean tracked-file audit with no raw data, generated OOS outputs,
   credentials, or gitlinks.
2. Evidence that protected paths are absent from the imported history, not
   only from the final tree.
3. `git log --follow` evidence for representative Dashboard and Niu Men files
   showing their source history remains reachable.
4. Passing source tests for the imported Python package and Dashboard web
   unit/build checks where the source repository already provides them.
5. A passing monorepo foundation checker updated for the new allowlist.
6. No changes to the original Dashboard or Niu Men working trees.
7. No change to the `research_snapshot.v2` contract or Niu Men strategy logic.

## Sequencing

The Dashboard PR lands first because it is the primary application boundary.
The Niu Men PR follows from the updated `main` and remains independently
reviewable. Only after both imports are stable should M2 extract shared
contract assets into `packages/research-core`.
