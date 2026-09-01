# Runtime and Data Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify project-owned runtime data under `~/data/trading-research-dashboard`, make the Alpaca/Redis live-market path explicitly runnable and testable, prepare the monorepo authoritative publication path, and remove the two obsolete local checkouts.

**Architecture:** Add one small Python configuration module as the source of truth for the project data root. Dashboard caches and research artifact defaults consume that module while external `market-data-platform` and `etf-minute-fetcher` roots remain explicit inputs. Keep scheduled publication in `shadow` until external production evidence exists; expose and validate manual `authoritative` runs without claiming cutover. Delete only the two clean local legacy directories after all repository checks pass.

**Tech Stack:** Python 3.11+, pytest, uv, FastAPI, Alpaca SDK, Redis, GitHub Actions, Vite/TypeScript.

**Spec:** `docs/superpowers/specs/2026-08-31-runtime-and-data-closeout-design.md`

## Global Constraints

- Do not copy raw market data or large research outputs into Git.
- Do not expose Alpaca credentials to browser code or `VITE_*` variables.
- Keep `market-data-platform` and `etf-minute-fetcher` as external source directories.
- Do not switch scheduled runs to authoritative without real production evidence.
- Delete only the two named legacy local checkouts, after clean-worktree checks; do not delete remote GitHub repositories.

---

### Task 1: Centralize project data-root configuration

**Files:**
- Create: `apps/dashboard/src/trading_research/data/config.py`
- Modify: `apps/dashboard/src/trading_research/data/data_sources.py`
- Modify: `apps/dashboard/src/trading_research/scripts/build_rbreaker_alpaca_artifact.py`
- Test: `apps/dashboard/tests/test_data_config.py`

**Interfaces:**
- Produces `project_data_root() -> Path`, `project_cache_root() -> Path`, and `project_artifact_root() -> Path`.
- Reads `TRADING_RESEARCH_DATA_ROOT`; default is `Path.home() / "data" / "trading-research-dashboard"`.
- Existing external data-root overrides remain supported.

- [ ] **Step 1: Write the failing tests** for the default root, environment override, and stable cache/artifact subdirectories.
- [ ] **Step 2: Run `uv run --locked --project apps/dashboard pytest -q apps/dashboard/tests/test_data_config.py` and confirm the new import/API fails.**
- [ ] **Step 3: Implement the minimal configuration module and replace hard-coded project-owned defaults.**
- [ ] **Step 4: Run the focused tests and the existing data-source tests; confirm they pass.**
- [ ] **Step 5: Commit the configuration change with `git add` and `git commit -m "feat: centralize dashboard data root"`.**

### Task 2: Make live-market configuration and readiness behavior explicit

**Files:**
- Modify: `apps/market-data-service/src/market_data_service/config.py`
- Modify: `apps/market-data-service/src/market_data_service/app.py`
- Modify: `apps/market-data-service/README.md`
- Modify: `apps/market-data-service/docs/runtime.md`
- Test: `apps/market-data-service/tests/test_app.py`
- Test: `apps/market-data-service/tests/test_config.py`

**Interfaces:**
- No new public quote protocol; preserve `/healthz`, `/readyz`, `/v1/quotes/{symbol}`, `/v1/bars/{symbol}`, and WebSocket endpoints.
- Service startup must distinguish historical provider availability from live collector availability.
- Missing Alpaca credentials means no live collector; missing Redis means local in-memory quote storage only.

- [ ] **Step 1: Add failing tests** asserting that no Alpaca collector is created without both credentials and that the selected historical provider still works without live credentials.
- [ ] **Step 2: Run the focused market-data tests and verify the new assertions fail for the intended reason.**
- [ ] **Step 3: Implement the smallest configuration/readiness changes and document the exact credential, Redis, and service-start requirements.**
- [ ] **Step 4: Run `uv run --locked --project apps/market-data-service pytest -q` and `uv run --locked --project apps/market-data-service ruff check src tests`.**
- [ ] **Step 5: Commit with `git add` and `git commit -m "feat: clarify live market runtime readiness"`.**

### Task 3: Close the authoritative publication handoff without pretending production cutover

**Files:**
- Modify: `.github/workflows/dashboard-report.yml`
- Modify: `docs/operations/runtime-cutover.md`
- Modify: `docs/roadmap/README.md`
- Test: `apps/dashboard/tests/test_workflow_contracts.py`
- Test: `apps/dashboard/tests/test_runtime_manifest.py`

**Interfaces:**
- Scheduled execution remains `SCHEDULE_MODE=shadow`.
- Manual dispatch continues to accept `shadow` and `authoritative`.
- Authoritative mode must validate `data.json.contextualResearch`, public URL, deployment credentials, and post-deploy smoke checks.

- [ ] **Step 1: Write failing workflow-contract tests** for the explicit manual authoritative path and the invariant that the scheduled default remains shadow.
- [ ] **Step 2: Run the focused workflow tests and verify the failure identifies the missing contract.**
- [ ] **Step 3: Update workflow and runbook wording so the monorepo is the sole normal publisher, old repositories are rollback-only, and external gates are clearly marked not-yet-verified.**
- [ ] **Step 4: Run foundation checks, workflow-contract tests, static-asset validation, frontend tests, and frontend build.**
- [ ] **Step 5: Commit with `git add` and `git commit -m "chore: close authoritative publication handoff"`.**

### Task 4: Validate data layout and clean obsolete local checkouts

**Files:**
- Modify: `docs/getting-started.md`
- Modify: `docs/maintenance/quality-audit.md`
- Test: `tests/test_foundation.py`

- [ ] **Step 1: Run the full repository verification commands and record exit codes before deletion.**
- [ ] **Step 2: Confirm both legacy directories are clean, on `main`, synchronized with `origin/main`, and contain rollback-only README/workflow state.**
- [ ] **Step 3: Confirm the migrated equivalents exist under `apps/dashboard/` and `packages/niu-men-line-strategy/`.**
- [ ] **Step 4: Use a recoverable move to `/tmp` for both local directories, then verify the new repository and data paths.**
- [ ] **Step 5: Run final `git status --short`, relevant tests, and path checks; report that remote repositories were not deleted.**
