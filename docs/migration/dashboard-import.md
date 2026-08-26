# Dashboard M1 import manifest

## Status

Dashboard M1 is active. This manifest records the reproducible, history-preserving
import boundary before the Dashboard history import.

Niu Men remains the next separate PR and is not included in this import.

## Source and rollback record

| Field | Value |
| --- | --- |
| Source repository | https://github.com/runchengxie/wu-t0-trading-dashboard |
| Exact source commit | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` |
| Destination prefix | `apps/dashboard/` |
| Import method | History-aware path filter from the exact source commit, merged with unrelated histories allowed |

The exact source commit is the Dashboard rollback point recorded in
[`source-commits.md`](source-commits.md).

## Included path map

The following source paths below `apps/dashboard/` are rewritten as shown:

```text
src/                                  -> apps/dashboard/src/
web/                                  -> apps/dashboard/web/
backtest/                             -> apps/dashboard/backtest/
tests/                                -> apps/dashboard/tests/
scripts/                              -> apps/dashboard/scripts/
docs/backtest.md                      -> apps/dashboard/docs/backtest.md
docs/cloudflare-workers.md            -> apps/dashboard/docs/cloudflare-workers.md
docs/configuration.md                 -> apps/dashboard/docs/configuration.md
docs/data-sources.md                  -> apps/dashboard/docs/data-sources.md
docs/indicators.md                    -> apps/dashboard/docs/indicators.md
docs/outputs.md                       -> apps/dashboard/docs/outputs.md
docs/research-snapshot.md             -> apps/dashboard/docs/research-snapshot.md
docs/troubleshooting.md               -> apps/dashboard/docs/troubleshooting.md
docs/web-frontend.md                  -> apps/dashboard/docs/web-frontend.md
schemas/research-snapshot.schema.json -> apps/dashboard/schemas/research-snapshot.schema.json
pyproject.toml                        -> apps/dashboard/pyproject.toml
uv.lock                               -> apps/dashboard/uv.lock
wrangler.jsonc                        -> apps/dashboard/wrangler.jsonc
README.md                             -> apps/dashboard/README.md
.gitignore                            -> apps/dashboard/.gitignore
```

## Excluded paths

The import excludes the following paths and path classes:

- `data/raw/`
- generated `web/public/data.json`
- generated `web/public/research.json`
- `.env*` and other credentials
- local environment files and caches
- legacy root scripts when their maintained equivalents already exist under
  `src/`
- source-repository CI files that would execute independently from the
  monorepo root

These exclusions are applied to rewritten history, not only deleted from the
final checkout. The imported history must not contain excluded files.

## Boundary guarantees

This import does not import source code for Niu Men, does not change Dashboard
application behavior, and does not change the `research_snapshot.v2` consumer
behavior. The existing source repositories remain active and unchanged during
M1.
