# R-Breaker and ICT Production Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Alpaca-to-Worker R-Breaker publication path and a separately identified, cost-aware ICT liquidity-reclaim research strategy.

**Architecture:** PR1 adds a manual artifact-producer workflow that uses the existing Alpaca producer, snapshot generator, contextual enrichment, validation, build, and optional Cloudflare deployment steps. PR2 adds a pure pandas strategy engine and snapshot producer for one objective liquidity-reclaim rule, then registers its distinct snapshot in the frontend without mixing its metrics into existing strategy comparisons.

**Tech Stack:** GitHub Actions, Python 3.11/uv, Alpaca historical API, pandas, JSON Schema, pytest, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-08-30-rbreaker-ict-production-design.md`

## Global Constraints

- Never print or persist `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, Cloudflare tokens, or artifact access tokens.
- Use Alpaca SIP by default and make IEX an explicit input.
- Reject incomplete sessions unless `--allow-incomplete` is explicitly selected.
- Do not commit raw minute bars or generated artifacts.
- Use next-bar-open execution for ICT signals; no same-bar fills.
- Do not label a single split as rolling OOS.
- Keep ICT strategy identity separate from R-Breaker and Niu Men.

---

### Task 1: Add PR1 workflow contract tests

**Files:**
- Modify: `apps/dashboard/tests/test_workflow_contracts.py`
- Test: `apps/dashboard/tests/test_workflow_contracts.py`

**Interfaces:**
- Consumes: `.github/workflows/rbreaker-artifact-and-deploy.yml` and existing workflow text.
- Produces: deterministic assertions for inputs, secret names, artifact name, feed default, enrichment ordering, validation, and credential-safe logging.

- [ ] **Step 1: Write failing workflow assertions**

Add tests that read the new workflow and assert `workflow_dispatch`, `symbol`, `session_date`, `feed` defaulting to `sip`, `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `rbreaker-input-v1`, `build_rbreaker_alpaca_artifact.py`, `enrich_contextual_research`, `validate_static_assets.py --require-contextual`, and a conditional Wrangler deploy. Assert the workflow does not contain commands that echo either secret value and that enrichment precedes strict validation.

- [ ] **Step 2: Run the focused tests**

Run:

```bash
TMPDIR=/path/to/tmp-dashboard uv run --locked pytest -q apps/dashboard/tests/test_workflow_contracts.py
```

Expected: the new contract test fails because the workflow file does not exist.

- [ ] **Step 3: Commit the red test**

```bash
git add apps/dashboard/tests/test_workflow_contracts.py
git commit -m "test: define Alpaca R-Breaker workflow contract"
```

### Task 2: Implement PR1 Alpaca producer/deploy workflow

**Files:**
- Create: `.github/workflows/rbreaker-artifact-and-deploy.yml`
- Modify: `.github/workflows/deploy-dashboard.yml`
- Modify: `.github/workflows/publish-rbreaker-snapshot.yml`
- Test: `apps/dashboard/tests/test_workflow_contracts.py`

**Interfaces:**
- Consumes: `build_rbreaker_alpaca_artifact.py`, `generate_rbreaker_snapshot.py`, contextual enrichment, static validation, and Wrangler config.
- Produces: a manual workflow with `rbreaker-input-v1` artifact output and optional deployment from the same run.

- [ ] **Step 1: Add the manual workflow**

Define inputs `symbol` (default `AAPL`), `session_date` (required ISO date), `feed` (`sip` default, `iex` alternative), `allow_incomplete` (false default), and `deploy` (false default). Configure Python 3.11 and `uv sync --locked --package trading-research-dashboard-app --extra alpaca --extra backtest`. Run the producer with the two Alpaca secrets in `env`, pass `--allow-incomplete` only when selected, validate the generated artifact, upload it as `rbreaker-input-v1`, generate `rbreaker-research.json`, run contextual enrichment, strict validation, frontend tests/build, and conditionally deploy with Wrangler. Write only symbol/date/feed/run metadata to the step summary.

- [ ] **Step 2: Align consumer artifact names**

Change the existing R-Breaker consumer default and deployment input description to `rbreaker-input-v1`, while retaining explicit `artifact_name` overrides where needed. Do not remove the existing cross-repository publisher.

- [ ] **Step 3: Run focused workflow tests**

Run the focused pytest command from Task 1. Expected: PASS.

- [ ] **Step 4: Commit PR1**

```bash
git add .github/workflows/rbreaker-artifact-and-deploy.yml .github/workflows/deploy-dashboard.yml .github/workflows/publish-rbreaker-snapshot.yml apps/dashboard/tests/test_workflow_contracts.py
git commit -m "ci: add Alpaca R-Breaker artifact deployment path"
```

### Task 3: Add objective ICT strategy red tests

**Files:**
- Create: `apps/dashboard/tests/test_ict_liquidity_reclaim.py`
- Create: `apps/dashboard/tests/fixtures/ict_liquidity_reclaim_minute.csv`

**Interfaces:**
- Consumes: planned `trading_research.strategies.ict_liquidity_reclaim.evaluate_session`.
- Produces: tests for long/short reclaim, next-bar entry, stop/target ordering, session-close exit, one-trade limit, costs, and malformed input rejection.

- [ ] **Step 1: Write fixture and failing tests**

Create a small timezone-aware US regular-session fixture with a previous-day high/low, one long reclaim, one short reclaim, a stop/target path, and bars after the first completed trade. Assert returned trade fields include `side`, `signal_time`, `entry_time`, `entry_price`, `exit_time`, `exit_price`, `gross_return`, `cost_return`, `net_return`, `mfe`, and `mae`.

- [ ] **Step 2: Run the focused tests**

Run:

```bash
TMPDIR=/path/to/tmp-dashboard uv run --locked --package trading-research-dashboard-app --extra test pytest -q apps/dashboard/tests/test_ict_liquidity_reclaim.py
```

Expected: FAIL because the strategy module does not exist.

- [ ] **Step 3: Commit the red tests**

```bash
git add apps/dashboard/tests/test_ict_liquidity_reclaim.py apps/dashboard/tests/fixtures/ict_liquidity_reclaim_minute.csv
git commit -m "test: define ICT liquidity reclaim behavior"
```

### Task 4: Implement ICT liquidity-reclaim engine

**Files:**
- Create: `apps/dashboard/src/trading_research/strategies/ict_liquidity_reclaim.py`
- Modify: `apps/dashboard/src/trading_research/strategies/__init__.py`
- Test: `apps/dashboard/tests/test_ict_liquidity_reclaim.py`

**Interfaces:**
- Consumes: `pd.DataFrame` with timezone-aware `datetime` index and `open/high/low/close/volume`, previous-day high/low, and `LiquidityReclaimConfig`.
- Produces: `validate_minute_bars`, `evaluate_session`, and a deterministic list of trade dictionaries.

- [ ] **Step 1: Implement input validation**

Require a timezone-aware, strictly increasing, duplicate-free index and positive OHLC values with `high >= max(open, close)`, `low <= min(open, close)`. Restrict evaluation to the configured regular session and fail when no bars remain.

- [ ] **Step 2: Implement signal and execution rules**

Detect long reclaim when `low < previous_day_low` and `close > previous_day_low`; detect short reclaim when `high > previous_day_high` and `close < previous_day_high`. Schedule entry at the next bar open. Set long stop below signal low and short stop above signal high using the configured buffer. Set target at `entry +/- risk * target_r`. Resolve same-bar stop/target touches conservatively as stop-first. Close remaining positions at the last session close. Enforce one completed trade per session.

- [ ] **Step 3: Implement costs and excursions**

Apply per-side bps and fixed per-side slippage in price units to entry and exit in the adverse direction. Return gross return, cost return, net return, MFE, and MAE using the bars available after entry and before exit.

- [ ] **Step 4: Run the focused tests**

Run the focused pytest command from Task 3. Expected: PASS.

- [ ] **Step 5: Run lint on changed Python files**

```bash
TMPDIR=/path/to/tmp-dashboard uv run --locked ruff check apps/dashboard/src/trading_research/strategies/ict_liquidity_reclaim.py apps/dashboard/tests/test_ict_liquidity_reclaim.py
```

Expected: PASS.

### Task 5: Add ICT snapshot producer and tests

**Files:**
- Create: `apps/dashboard/src/trading_research/scripts/generate_ict_liquidity_reclaim_snapshot.py`
- Create: `apps/dashboard/tests/test_generate_ict_liquidity_reclaim_snapshot.py`
- Create: `apps/dashboard/tests/fixtures/ict_liquidity_reclaim_snapshot.json`
- Test: `packages/research-core/tests/test_strategy_snapshot.py`

**Interfaces:**
- Consumes: normalized minute bars, previous-day levels, strategy config, and optional producer run ID.
- Produces: `generate_snapshot(...) -> dict[str, Any]` with `strategy.id = "ict-liquidity-reclaim"`, distinct provenance, explicit costs, and date-based non-rolling OOS summary.

- [ ] **Step 1: Write snapshot contract tests**

Assert the strategy identity, date fields, coverage, metrics, execution timing, cost details, provenance, and schema validation. Assert that `walkForward.semantics` says a single date split or session sample rather than rolling OOS.

- [ ] **Step 2: Run the focused snapshot tests**

Run:

```bash
TMPDIR=/path/to/tmp-dashboard uv run --locked --package trading-research-dashboard-app --extra test pytest -q apps/dashboard/tests/test_generate_ict_liquidity_reclaim_snapshot.py packages/research-core/tests/test_strategy_snapshot.py
```

Expected: FAIL because the snapshot producer does not exist.

- [ ] **Step 3: Implement the producer**

Load and validate the fixture/data input, call `evaluate_session`, aggregate finite metrics, preserve nulls for unavailable metrics, attach input checksum and run ID when supplied, and validate the final envelope before atomic write.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2. Expected: PASS.

### Task 6: Register and display the ICT strategy

**Files:**
- Modify: `apps/dashboard/web/src/research/strategyRegistry.ts`
- Modify: `apps/dashboard/web/src/research/strategySnapshot.ts` if strategy-specific details need typing.
- Create or modify: `apps/dashboard/web/public/ict-liquidity-reclaim-research.json` only with a reviewed fixture snapshot, never raw minute data.
- Test: `apps/dashboard/web/src/researchRegistry.test.mjs` or the existing registry test file.

**Interfaces:**
- Consumes: generic strategy snapshot v1.
- Produces: a separate `ict-liquidity-reclaim` strategy definition and user-visible label/description.

- [ ] **Step 1: Add failing registry test**

Assert the ICT strategy is present with its own snapshot path and is not assigned the R-Breaker or Niu Men ID.

- [ ] **Step 2: Register the strategy**

Add the ICT definition and load it through the existing generic envelope parser. Keep the comparison logic’s missing/non-shared variant states intact.

- [ ] **Step 3: Run frontend tests and build**

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

Expected: PASS.

### Task 7: Full verification, split PRs, and handoff

**Files:**
- Modify: relevant docs and workflow comments only after behavior is verified.

- [ ] **Step 1: Run complete verification**

```bash
TMPDIR=/path/to/tmp-dashboard uv run --locked --extra test --extra backtest --extra alpaca pytest -q
TMPDIR=/path/to/tmp-dashboard uv run --locked ruff check .
TMPDIR=/path/to/tmp-dashboard uv run --locked ruff format --check .
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
TMPDIR=/path/to/tmp-dashboard uv run --project packages/research-core pytest -q
```

- [ ] **Step 2: Create PR1 from the PR1 commits**

Push the workflow commits, create a PR against `main`, verify checks and diff, and merge only if the workflow contract and full verification pass.

- [ ] **Step 3: Create PR2 from updated main**

Create a fresh branch from the merged main, add only the ICT strategy/snapshot/registry changes, run the full verification again, and open a separate PR.

- [ ] **Step 4: Merge and clean**

After each PR is merged, fast-forward local `main`, delete the remote and local feature branch, remove only clean worktrees, and report any retained artifacts or deployment limitations.
