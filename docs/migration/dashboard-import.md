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

## Validation audit (2026-08-26)

Validation was run from the M1 migration worktree after the Dashboard import
and governance integration. The nested Dashboard command deliberately omits
`--extra dev`, because `apps/dashboard/pyproject.toml` declares its test tools
in a dependency group.

| Command | Exact result |
| --- | --- |
| `uv run --project apps/dashboard --locked pytest -q` (from `apps/dashboard/`) | Failed: `Project directory apps/dashboard does not exist` |
| `uv run --project . --locked pytest -q` (from `apps/dashboard/`) | `33 passed in 7.61s` |
| `uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests` | `33 passed in 5.90s` |
| `npm ci --prefix apps/dashboard/web` | Added 39 packages; audited 40 packages; `found 0 vulnerabilities` |
| `npm test --prefix apps/dashboard/web -- --run` | `23` tests passed; `0` failed |
| `npm run build --prefix apps/dashboard/web` | `tsc && vite build` completed successfully; 632 modules transformed |
| `uv lock --check` | `Resolved 7 packages in 0.60ms` |
| `uv run --locked --extra dev pytest -q` | `21 passed in 1.55s` |
| `uv run --locked python scripts/check_foundation.py` | `Foundation check passed` |
| `git status --short` | No output; working tree clean before this documentation-only audit update |
| `git diff --check` | No output; exit status 0 |

The web production build emitted Vite's non-fatal warning that the minified
JavaScript chunk is above 800 kB. No migration-specific runtime failure was
reported.

Three import-specific validation compatibility defects were corrected without
changing Dashboard runtime logic: the web package now exposes the plan's
`npm test` entry point, and its schema test uses the retained v2 fixture rather
than excluded generated `web/public/research.json`. The foundation checker now
skips ignored dependency documentation, so the required `npm ci` directory is
not scanned for placeholder markers. Regression coverage verifies that ignore
boundary.

Inherited tests now use the history-preserved
`trading_research.data.data_sources` package module, packaged module entry
points, and retained contract assets. This removes their dependency on
intentionally excluded source-root modules and source CI.

Representative preserved-history evidence:

```text
$ git log --follow --oneline -- apps/dashboard/src/trading_research/dashboard/astock_tech.py | head -20
5a7de4d refactor: package dashboard Python modules
```

The deterministic protected-history query covers every explicit exclusion and
was empty:

```text
$ git log --all --name-only --format= | grep -E '^(apps/dashboard/(data/|artifacts/|web/public/|\.github/|docs/superpowers/)|apps/dashboard/(astock_tech\.py|data_sources\.py)$|apps/dashboard/(.*/)?\.env[^/]*$|apps/dashboard/(.*/)?[^/]*(credential|secret|token|password)[^/]*$|apps/dashboard/(.*/)?[^/]*\.(pem|key|p12|pfx)$)' || test $? -eq 1
(no output)
```

The gitlink and submodule audits were also empty:

```text
$ git ls-files --stage | awk '$1 == "160000" {print}'
(no output)
$ git submodule status
(no output)
```

The original Dashboard working tree at
`/path/to/user/code/wu-t0-trading-dashboard` remained unchanged:

```text
$ git -C /path/to/user/code/wu-t0-trading-dashboard status --short
(no output)
$ git -C /path/to/user/code/wu-t0-trading-dashboard rev-parse --short HEAD
e03617a
```
