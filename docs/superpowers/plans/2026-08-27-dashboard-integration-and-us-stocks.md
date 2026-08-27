# Dashboard Integration and US Stocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge the prepared R-Breaker, editorial UI, and Redis branches into `main`, then add the approved default US instruments and dynamic US ticker selection to the Dashboard.

**Architecture:** Preserve the existing branch boundaries and merge each tested feature branch into `main` in dependency order. Implement US defaults in the Dashboard configuration layer, while allowing explicit US tickers to inherit the existing stock defaults without inventing market data or changing the service API.

**Tech Stack:** Git worktrees, Python 3.11+, pytest, uv workspace, React/Vite, Node test runner.

**Spec:** Existing approved market support design at `docs/superpowers/specs/2026-08-27-hk-us-market-support-design.md` and the prior Dashboard default-US-stocks request.

## Global Constraints

- Do not modify or delete unrelated user worktree changes.
- Do not generate or hand-edit market data snapshots.
- Preserve CN/HK behavior and existing cache fallback behavior.
- Keep `main` changes merge-only; implement new US behavior on `feat/dashboard-default-us-stocks`.
- Do not claim tests pass without fresh command output.

---

### Task 1: Merge prepared feature branches

**Files:** Git history only; no source edits.

- [ ] Verify all three source worktrees are clean and branches are descendants of the current `main` or contain an explicit merge base.
- [ ] Merge `feat/rbreaker-production-publication`, then `feat/dashboard-editorial-ui`, then `feat/m5-redis-state` into `main`, resolving only integration conflicts caused by the moving base.
- [ ] Run `git diff --check` and inspect `git log --graph` after each merge.

### Task 2: Add failing tests for default US instruments

**Files:**
- Modify: `apps/dashboard/tests/test_default_instrument.py`
- Modify: `apps/dashboard/tests/test_cli.py`

- [ ] Assert the default configuration order is `sz300246`, `AAPL.US`, `MSFT.US`, `NVDA.US`, `TSLA.US`, with US market metadata and USD/New York profile behavior.
- [ ] Add a test that explicit `codes=["AAPL.US", "TSLA.US"]` creates those instruments even though they are not preconfigured in the original configuration map.
- [ ] Run the focused tests and confirm they fail because the current configuration still contains only 宝莱特 and filters unknown codes.

### Task 3: Implement US defaults and dynamic explicit selection

**Files:**
- Modify: `apps/dashboard/src/trading_research/dashboard/astock_tech.py`

- [ ] Add four default stock entries with names Apple/Microsoft/NVIDIA/Tesla, `market="US"`, and `instrument_type="stock"`.
- [ ] Normalize explicit US codes into configuration entries using the existing market profile and stock defaults; keep unknown CN/HK codes ignored as before.
- [ ] Run the focused Dashboard tests and verify the new behavior passes.

### Task 4: Reconcile project status documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap/README.md`
- Modify: `apps/dashboard/README.md`

- [ ] Document that #44 is in `main`, the three prepared branches have been integrated, and the Dashboard defaults include AAPL/MSFT/NVDA/TSLA.
- [ ] Keep M6 runtime cutover and any genuinely incomplete production-readiness gates marked incomplete.
- [ ] Run documentation/foundation checks.

### Task 5: Full verification and merge US support

**Files:** Git history only after verification.

- [ ] Run available Python tests, frontend unit tests, build, Ruff, foundation check, and `git diff --check` with the repository's actual environment configuration.
- [ ] If the repository Python environment is stale, repair only the local environment or use a temporary cache; do not alter dependency declarations solely to hide an environment failure.
- [ ] Commit the US support changes, merge `feat/dashboard-default-us-stocks` into `main`, and re-run the final status/log checks.
