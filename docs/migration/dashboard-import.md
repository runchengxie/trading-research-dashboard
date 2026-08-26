# Dashboard M1 import manifest

## Status

Dashboard M1 is imported. This manifest records the reproducible,
history-preserving import boundary and post-import verification basis.

Niu Men remains the next separate PR and is not included in the completed
Dashboard import.

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

The following source-root paths are the complete allowlist. Each listed source
path is rewritten to the corresponding destination path shown below:

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

Every source-root path not listed in this allowlist is excluded from the
import. For recursive entries, the entry includes its descendants except for
the explicit exclusions below.

## Explicit exclusions

The following source-root paths and patterns are excluded from the fixed source
commit:

- `data/raw/**`
- `web/public/data.json`
- `web/public/research.json`
- `.github/**`
- `.env*` at the source root
- `**/.env*` in any source directory
- `**/*credential*`
- `**/*secret*`
- `**/*token*`
- `**/*password*`
- `**/*.pem`
- `**/*.key`
- `**/*.p12`
- `**/*.pfx`
- `astock_tech.py` at the source root
- `data_sources.py` at the source root
- `docs/superpowers/**`

These exclusions are applied to rewritten history, not only deleted from the
final checkout. The fixed source commit plus this allowlist and exclusion
pattern set therefore determines the complete history filter; the imported
history must not contain excluded files.

## Boundary guarantees

This import does not import source code for Niu Men, does not change Dashboard
application behavior, and does not change the `research_snapshot.v2` consumer
behavior. The existing source repositories remain active and unchanged during
M1.
