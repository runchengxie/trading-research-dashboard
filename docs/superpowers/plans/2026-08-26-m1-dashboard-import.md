# M1 Dashboard Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import Dashboard into `apps/dashboard/` with useful source history preserved while excluding raw data, generated snapshots, credentials, and unrelated automation.

**Architecture:** Filter the exact Dashboard source commit into a temporary history with selected paths renamed below `apps/dashboard/`, then merge that history into the monorepo. The root project remains the integration shell; nested Dashboard metadata and compatibility entry points remain until M3.

**Tech Stack:** `git-filter-repo` via `uvx`, Git, Python/uv, pytest, Node.js/npm, Vite, and the existing foundation checker.

**Spec:** `docs/superpowers/specs/2026-08-26-m1-history-preserving-imports-design.md`

## Global Constraints

- Use Dashboard source commit `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114`.
- Destination is `apps/dashboard/`; do not import Dashboard into the root package.
- Exclude `data/raw/`, `web/public/data.json`, `web/public/research.json`, `.env*`, caches, source-repository CI, and superseded legacy root scripts.
- Do not import Niu Men, `research-workspace`, `market-data-platform`, or `etf-minute-fetcher` in this PR.
- Preserve `research_snapshot.v2`, Dashboard behavior, and the current selected instrument.
- Do not create submodules, gitlinks, committed temporary remotes, or a root uv workspace.
- Keep original Dashboard and Niu Men working trees unchanged.
- Keep Python `>=3.11`.

---

### Task 1: Record the Dashboard import manifest

**Files:**
- Create: `docs/migration/dashboard-import.md`
- Modify: `docs/migration/source-commits.md`
- Modify: `docs/migration/README.md`

**Interfaces:**
- Consumes: the M1 design spec and the exact Dashboard source commit.
- Produces: a reproducible source path map, exclusion list, and rollback record.

- [ ] **Step 1: Document the exact path map**

The manifest must map these source paths below `apps/dashboard/`:

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

List the excluded paths explicitly and state that exclusions are applied to
rewritten history, not only deleted from the final checkout.

- [ ] **Step 2: Update migration status**

Mark Dashboard M1 as active, keep Niu Men as the next separate PR, and retain
the source commit in `docs/migration/source-commits.md`.

- [ ] **Step 3: Verify and commit documentation**

```bash
rg -n "8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114|data/raw|research.json|apps/dashboard" docs/migration
git diff --check
git add docs/migration
git commit -m "docs: record Dashboard M1 import manifest"
```

### Task 2: Filter and merge Dashboard history

**Files:**
- Add: history-preserved files under `apps/dashboard/` according to Task 1.
- Modify: `apps/dashboard/README.md` only to add the monorepo boundary note.

**Interfaces:**
- Consumes: `docs/migration/dashboard-import.md` and source commit `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114`.
- Produces: a merge commit with source history preserved and protected paths absent from imported history.

- [ ] **Step 1: Create a temporary source clone**

```bash
IMPORT_TMP=$(mktemp -d)
git clone --no-local /path/to/user/code/wu-t0-trading-dashboard "$IMPORT_TMP/dashboard"
cd "$IMPORT_TMP/dashboard"
git checkout --detach 8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114
```

- [ ] **Step 2: Rewrite paths with git-filter-repo**

Run `uvx --from git-filter-repo git-filter-repo --force` with the Task 1
`--path` entries and matching `--path-rename` entries. Rename the five
directories (`src`, `web`, `backtest`, `tests`, `scripts`) and every listed
file into its `apps/dashboard/` destination. Then run a second filter with:

```bash
uvx --from git-filter-repo git-filter-repo --force --invert-paths \
  --path apps/dashboard/web/public/data.json \
  --path apps/dashboard/web/public/research.json
```

The filtered clone must contain no `data/`, `artifacts/`, `.env*`, or source
CI paths before it is merged.

- [ ] **Step 3: Merge and clean up the filtered history**

From the migration worktree, run:

```bash
git remote add dashboard-m1 "$IMPORT_TMP/dashboard"
git fetch dashboard-m1 HEAD
git merge --allow-unrelated-histories --no-commit FETCH_HEAD
```

Resolve only the marker conflict at `apps/dashboard/README.md` by retaining
the imported README and adding a short monorepo boundary note. Commit the
merge, remove the temporary remote, and remove the temporary clone.

- [ ] **Step 4: Verify history boundaries**

```bash
git log --follow --oneline -- apps/dashboard/src/trading_research/dashboard/astock_tech.py | head -20
git log --all --name-only --format= -- apps/dashboard/data apps/dashboard/web/public/data.json apps/dashboard/web/public/research.json
git ls-files --stage | awk '$1 == "160000" {print}'
git submodule status
git diff --check
```

The protected-path, gitlink, and submodule queries must be empty.

### Task 3: Integrate Dashboard with monorepo governance

**Files:**
- Modify: `scripts/check_foundation.py`
- Modify: `tests/test_foundation.py`
- Modify: `README.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/source-commits.md`
- Modify: `.github/workflows/foundation.yml` only for minimum path-aware validation.

**Interfaces:**
- Consumes: the imported `apps/dashboard/` tree and Task 1 manifest.
- Produces: an explicit M1 allowlist that accepts Dashboard paths and rejects protected or unrelated paths.

- [ ] **Step 1: Add failing boundary tests**

Extend the temporary-repository tests with accepted paths:

```python
"apps/dashboard/src/trading_research/dashboard/astock_tech.py"
"apps/dashboard/web/src/App.tsx"
```

and rejected paths:

```python
"apps/dashboard/data/raw/example.csv"
"apps/dashboard/web/public/research.json"
"apps/dashboard/.env"
"packages/niu-men-line-strategy/src/placeholder.py"
```

- [ ] **Step 2: Update the checker**

Replace the M0-only exact-file set with an explicit M1 allowlist retaining all
foundation files and permitting only the Task 1 Dashboard paths. Keep explicit
forbidden checks for raw data, generated snapshots, artifacts, credentials,
gitlinks, and external project directories.

- [ ] **Step 3: Update status documentation**

Change the root README from M0-only wording to state that Dashboard M1 is
imported but the monorepo is not yet the runtime source of truth. Keep Niu Men
as the next separate import and link the Dashboard manifest.

- [ ] **Step 4: Verify and commit governance changes**

```bash
uv run --locked --extra dev pytest tests/test_foundation.py -q
uv run --locked python scripts/check_foundation.py
git add scripts/check_foundation.py tests/test_foundation.py README.md docs/migration .github/workflows/foundation.yml
git commit -m "build: integrate Dashboard M1 boundary checks"
```

### Task 4: Validate Dashboard Python and web application

**Files:**
- Modify: none unless a concrete import-specific compatibility defect is found.
- Test: `apps/dashboard/tests/` and `apps/dashboard/web/`.

**Interfaces:**
- Consumes: the completed Dashboard import and M1 governance checker.
- Produces: reproducible verification evidence for the Dashboard PR.

- [ ] **Step 1: Run nested Python tests**

```bash
uv run --project apps/dashboard --locked --extra dev pytest -q
```

- [ ] **Step 2: Run web tests and production build**

```bash
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web -- --run
npm run build --prefix apps/dashboard/web
```

- [ ] **Step 3: Run monorepo verification**

```bash
uv lock --check
uv run --locked --extra dev pytest -q
uv run --locked python scripts/check_foundation.py
git status --short
git diff --check
```

- [ ] **Step 4: Record the audit**

Append exact command results, representative `git log --follow` output, the
empty protected-path history query, and confirmation that the original
Dashboard working tree is unchanged to `docs/migration/dashboard-import.md`.

### Task 5: Publish the Dashboard migration PR

**Files:**
- Modify: `docs/migration/dashboard-import.md` with final verification output.

**Interfaces:**
- Consumes: all Dashboard import and validation commits.
- Produces: an independently reviewable PR against `main`; no merge is done by this plan.

- [ ] **Step 1: Create the migration branch from the reviewed work**

The final branch name is `feat/m1-dashboard-history-import`; it must contain
only Dashboard M1 changes and the approved spec/plan documentation.

- [ ] **Step 2: Push and create the PR**

```bash
git push -u origin feat/m1-dashboard-history-import
gh pr create --base main --head feat/m1-dashboard-history-import \
  --title "feat: import Dashboard history into monorepo" \
  --body-file docs/migration/dashboard-import.md
```

- [ ] **Step 3: Stop for review**

Do not merge or delete the branch/worktree until the Dashboard PR is reviewed
and explicitly approved. Niu Men receives a separate plan and PR after this
one lands.
