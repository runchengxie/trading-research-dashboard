# Contextual Research Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the contextual research layer with multi-day conditional statistics, richer point-in-time context, hardened contracts, and a factual Dashboard checklist.

**Architecture:** Keep one-day `contextualResearch` as the observational source and add an optional independent `conditionalResearch` artifact for multi-day aggregation. Extend existing v1 payloads only with optional fields, validate nested contracts centrally, and let React render supplied results without recalculating research logic.

**Tech Stack:** Python 3.11, pandas, jsonschema, pytest, React, TypeScript, Node test runner, Vite.

**Spec:** `docs/superpowers/specs/2026-08-30-contextual-research-completion-design.md`

## Global Constraints

- Do not change `trading_research.strategy_snapshot.v1`.
- Do not add a third-party economic-calendar provider.
- Do not infer strategy-conditional metrics from aggregate strategy metrics.
- Keep `contextualResearch` and `conditionalResearch` optional for old Dashboard documents.
- Treat prior-day/prior-week levels and trigger inputs as point-in-time data only.
- Treat day archetype, completed-day VWAP, completed-day intermarket extremes, and forward outcomes as ex-post research data.
- Do not commit raw market data, credentials, build output, or large generated artifacts.

---

### Task 1: Conditional Research Contract and Aggregator

**Files:**
- Create: `packages/research-core/src/research_core/schemas/conditional-research.v1.schema.json`
- Modify: `packages/research-core/src/research_core/contextual.py`
- Modify: `packages/research-core/src/research_core/__init__.py`
- Create: `apps/dashboard/src/trading_research/dashboard/contextual_history.py`
- Create: `apps/dashboard/tests/test_contextual_history.py`
- Create: `packages/research-core/tests/test_conditional.py`
- Modify: `packages/research-core/README.md`

**Interfaces:**
- `CONDITIONAL_RESEARCH_VERSION: str`
- `validate_conditional_research(payload: Mapping[str, Any]) -> None`
- `aggregate_contextual_history(snapshots: Sequence[Mapping[str, Any]], *, strategy_outcomes: Sequence[Mapping[str, Any]] | None = None, generated_at: str) -> dict[str, Any]`

- [ ] **Step 1: Write failing contract and aggregation tests**

Create a two-date fixture with one setup event per date and one normalized strategy outcome. Assert the output version, date range, group dimensions, sample counts, win rate, expectancy, MFE, MAE, and coverage. Add invalid-contract tests for missing `groups` and invalid metric types.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
../../.venv/bin/python -m pytest -q packages/research-core/tests/test_conditional.py apps/dashboard/tests/test_contextual_history.py
```

Expected: import/version failures because the contract and aggregator do not exist.

- [ ] **Step 3: Add the conditional schema and validator**

Define explicit `dimensions`, `metrics`, `coverage`, `quality`, and `provenance` objects. Export the version and validator through `research_core`. Keep nullable dimensions explicit rather than allowing arbitrary properties.

- [ ] **Step 4: Implement deterministic group aggregation**

Normalize each setup event into a group keyed by instrument, market, session, day archetype, event type, and reference level. Normalize strategy outcomes into groups keyed by strategy, variant, instrument, session, event type, and reference level, enriching dimensions from the matching context when available. Aggregate valid return/mfe/mae values with arithmetic means; calculate win rate from explicit `win` or positive return; calculate expectancy as mean return; track unique dates and instruments.

- [ ] **Step 5: Run focused tests and lint**

Run the focused pytest command again and:

```bash
uv run --locked --package research-core ruff check packages/research-core/src packages/research-core/tests
uv run --locked --package trading-research-dashboard-app ruff check apps/dashboard/src apps/dashboard/tests
```

- [ ] **Step 6: Commit the conditional artifact slice**

```bash
git add packages/research-core apps/dashboard/src/trading_research/dashboard/contextual_history.py apps/dashboard/tests/test_contextual_history.py
git commit -m "feat: add contextual conditional research aggregation"
```

---

### Task 2: Complete Reference Levels, Sessions, and Event Time Semantics

**Files:**
- Modify: `packages/research-core/src/research_core/schemas/market-context.v1.schema.json`
- Modify: `packages/research-core/src/research_core/schemas/setup-event.v1.schema.json`
- Modify: `apps/dashboard/src/trading_research/dashboard/contextual_research.py`
- Modify: `apps/dashboard/src/trading_research/dashboard/event_study.py`
- Create: `apps/dashboard/tests/test_contextual_completion.py`
- Modify: `apps/dashboard/tests/test_event_study.py`

**Interfaces:**
- `semantic_reference_levels()` adds previous-week levels, session levels, and opening gap feature inputs without using current-day final data as a trigger.
- `session_for_timestamp()` converts offset-aware timestamps into the requested instrument timezone.
- Setup events may include optional `context` and `trigger` metadata.

- [ ] **Step 1: Write failing tests for previous-week/session fields and timezone normalization**

Assert previous-week high/low exclude the research date, session summaries expose open/close/volume/volumeShare and first extreme timestamps, setup events carry HTF/day-type context and trigger bar count, and a UTC event converted to New York is included in the same study as its local equivalent.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
../../.venv/bin/python -m pytest -q apps/dashboard/tests/test_contextual_completion.py apps/dashboard/tests/test_event_study.py
```

Expected: failures for missing fields and timezone-aware comparisons.

- [ ] **Step 3: Extend schemas with optional fields**

Add semantic level kinds `previous_week_high`, `previous_week_low`, `session_open`, `session_high`, and `session_low`. Add optional session fields and optional setup `context`/`trigger` objects. Add `gapPct`, `highTime`, and `lowTime` as optional context features.

- [ ] **Step 4: Implement point-in-time-safe derivation**

Use daily rows strictly before the research date for prior-week levels and prior close. Preserve existing ORB/VWAP availability rules. Retain intraday volume when present, calculate session volume share only when total volume is positive, and record first timestamps for session/day extrema. Populate setup context from the already-built market context and trigger metadata from the detector rule.

- [ ] **Step 5: Normalize event-study and session timestamps**

Treat naive timestamps as instrument-local, localize offset-aware timestamps to the stock timezone, and compare all windows on timezone-aware frames. Serialize study timestamps as local wall-clock strings to preserve the existing wire format.

- [ ] **Step 6: Run focused tests and regression tests**

Run:

```bash
../../.venv/bin/python -m pytest -q apps/dashboard/tests/test_contextual_research.py apps/dashboard/tests/test_contextual_completion.py apps/dashboard/tests/test_event_study.py apps/dashboard/tests/test_contextual_snapshot.py
```

- [ ] **Step 7: Commit the context completion slice**

```bash
git add packages/research-core/src/research_core/schemas apps/dashboard/src/trading_research/dashboard apps/dashboard/tests
git commit -m "feat: complete contextual reference and session semantics"
```

---

### Task 3: Enrichment CLI and Publication Validation

**Files:**
- Modify: `apps/dashboard/src/trading_research/scripts/enrich_contextual_research.py`
- Modify: `apps/dashboard/scripts/validate_static_assets.py`
- Create: `apps/dashboard/tests/test_contextual_publication.py`
- Modify: `.github/workflows/dashboard-report.yml`
- Modify: `.github/workflows/deploy-dashboard.yml`
- Modify: `apps/dashboard/docs/contextual-research.md`

**Interfaces:**
- `enrich_document(document, *, events=None, history_documents=None, strategy_outcomes=None) -> dict[str, Any]`
- CLI flags `--history` (repeatable JSON source paths) and `--strategy-outcomes`.
- Dashboard documents may contain optional `conditionalResearch` validated by `validate_conditional_research`.

- [ ] **Step 1: Write failing publication tests**

Assert history inputs produce `conditionalResearch`, missing history preserves current output, malformed contextual data is rejected before output replacement, and malformed conditional data is rejected by static validation.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
../../.venv/bin/python -m pytest -q apps/dashboard/tests/test_contextual_publication.py apps/dashboard/tests/test_enrich_contextual_research.py apps/dashboard/tests/test_static_assets.py
```

- [ ] **Step 3: Add history loading and atomic enrichment**

Load either a full Dashboard document or a contextual snapshot from each `--history` path, extract validated contextual payloads, load normalized strategy outcome rows, and attach the generated conditional artifact only when history is supplied. Validate both contextual and conditional payloads before replacing the output file.

- [ ] **Step 4: Harden static release validation**

When optional `contextualResearch` or `conditionalResearch` exists, validate it with the canonical research-core validators; keep `--require-contextual` as the authoritative presence/coverage gate.

- [ ] **Step 5: Wire optional workflow inputs**

Add workflow dispatch inputs for newline/comma-separated history source paths only where the runner has access to them, pass them to enrichment, and preserve the existing default behavior when omitted. Do not enable new automatic triggers.

- [ ] **Step 6: Update documentation and run focused tests**

Document the normalized strategy outcome shape, history command, empty-state semantics, and the fact that the workflow does not fetch event calendars. Run the focused tests and Ruff.

- [ ] **Step 7: Commit the publication slice**

```bash
git add apps/dashboard/src/trading_research/scripts/enrich_contextual_research.py apps/dashboard/scripts/validate_static_assets.py apps/dashboard/tests .github/workflows apps/dashboard/docs/contextual-research.md
git commit -m "feat: publish conditional contextual research artifacts"
```

---

### Task 4: Contextual Snapshot Schema Hardening

**Files:**
- Modify: `packages/research-core/src/research_core/schemas/contextual-snapshot.v1.schema.json`
- Modify: `packages/research-core/tests/test_contextual.py`
- Modify: `apps/dashboard/web/src/contextualResearch.ts`
- Modify: `apps/dashboard/web/src/contextualResearch.test.mjs`

**Interfaces:**
- The standalone contextual snapshot schema validates nested market contexts, setup events, and event studies.
- `parseConditionalResearch(value: unknown): ConditionalResearchSnapshot | null` validates the conditional artifact for frontend use.

- [ ] **Step 1: Write failing schema/parser tests**

Use a malformed nested context to assert standalone JSON Schema rejection. Add parser fixtures for valid/unsupported/malformed conditional artifacts and missing optional values.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
node --test apps/dashboard/web/src/contextualResearch.test.mjs
```

Expected: standalone schema test and conditional parser imports fail.

- [ ] **Step 3: Embed nested definitions and add strict parser checks**

Keep the schema self-contained and offline. Add required primitive checks for nested fields used by the UI, provenance checks, and conditional group metric checks. Return `null` on any unsupported or malformed optional artifact.

- [ ] **Step 4: Run frontend tests and build**

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

- [ ] **Step 5: Commit the contract hardening slice**

```bash
git add packages/research-core/src/research_core/schemas/contextual-snapshot.v1.schema.json packages/research-core/tests/test_contextual.py apps/dashboard/web/src/contextualResearch.ts apps/dashboard/web/src/contextualResearch.test.mjs
git commit -m "fix: harden contextual snapshot contract validation"
```

---

### Task 5: Setup Checklist and Conditional Statistics UI

**Files:**
- Modify: `apps/dashboard/web/src/App.tsx`
- Modify: `apps/dashboard/web/src/types.ts`
- Modify: `apps/dashboard/web/src/contextualResearch.ts`
- Modify: `apps/dashboard/web/src/components/ContextualResearchPanel.tsx`
- Modify: `apps/dashboard/web/src/components/SelectedInstrumentWorkspace.tsx`
- Modify: `apps/dashboard/web/src/contextualResearchPanel.test.mjs`
- Create: `apps/dashboard/web/src/conditionalResearch.test.mjs`
- Modify: `apps/dashboard/web/src/editorial.css`
- Modify: `apps/dashboard/web/tests/e2e/dashboard.spec.mjs`

**Interfaces:**
- `DashboardData` accepts optional `conditionalResearch`.
- `selectConditionalResearch(snapshot, instrumentCode, context, events)` returns matching groups.

- [ ] **Step 1: Write failing UI/parser tests**

Assert the panel exposes checklist rows for HTF, day archetype, session, reference level, and intermarket; supplied matching groups render sample count and expectancy; absent conditional data renders an explicit empty state; no ICT/confluence score is present.

- [ ] **Step 2: Run frontend focused tests and confirm RED**

Run:

```bash
node --test apps/dashboard/web/src/contextualResearchPanel.test.mjs apps/dashboard/web/src/conditionalResearch.test.mjs
```

- [ ] **Step 3: Implement conditional parser and selection**

Parse the optional artifact, select groups by instrument/context dimensions, and keep unmatched or malformed data out of the workspace.

- [ ] **Step 4: Render factual checklist and stats**

Render condition status and historical sample count, followed by outcome metrics only when supplied. Use “无多日条件统计” when no conditional artifact is present. Keep tables horizontally scrollable on small screens.

- [ ] **Step 5: Add E2E assertions and run frontend verification**

Add fixture-based E2E assertions for the panel and run:

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npm run test:e2e --prefix apps/dashboard/web
```

- [ ] **Step 6: Commit the UI slice**

```bash
git add apps/dashboard/web
git commit -m "feat: show contextual setup checklist and conditional stats"
```

---

### Task 6: Full Verification and PR Handoff

**Files:**
- Modify: `docs/roadmap/README.md`
- Modify: `apps/dashboard/docs/contextual-research.md`

- [ ] **Step 1: Run repository verification**

Run the repository foundation workflow commands locally with the available environment:

```bash
uv lock --check
uv run --locked python scripts/check_foundation.py
../../.venv/bin/python -m pytest -q
../../.venv/bin/python -m pytest -q apps/dashboard/tests
../../.venv/bin/python -m pytest -q packages/research-core/tests
uv run --locked --package research-core ruff check packages/research-core/src packages/research-core/tests
uv run --locked --package trading-research-dashboard-app ruff check apps/dashboard/src apps/dashboard/scripts apps/dashboard/tests
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

- [ ] **Step 2: Validate release snapshots and generated contracts**

Run:

```bash
../../.venv/bin/python apps/dashboard/scripts/validate_static_assets.py --require-contextual
../../.venv/bin/python -m pytest -q tests/test_foundation.py tests/test_research_contract_sync.py tests/test_runtime_workflow.py tests/test_deploy_workflow.py
```

- [ ] **Step 3: Inspect diff and worktree**

Check `git diff --check`, `git status`, tracked file boundaries, no credentials/raw data/build output, and confirm only the intended optional Dashboard fields were added.

- [ ] **Step 4: Update docs with verified results**

Record the final artifact commands and any environment-only E2E limitation without claiming unrun checks.

- [ ] **Step 5: Commit documentation and hand off PR branches**

```bash
git add docs/roadmap/README.md apps/dashboard/docs/contextual-research.md
git commit -m "docs: record contextual research completion"
```
