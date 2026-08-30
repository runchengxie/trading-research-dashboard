# Niu Men Calendar-Aware Folds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve real per-fold test-date evidence in Niu Men snapshots and render exact dates or honest date ranges instead of opaque ordinal windows.

**Architecture:** The Niu Men exporter will derive a calendar metadata object from the already available per-symbol fold rows, while retaining the existing cross-sectional metrics and v2 wire version. The shared adapter and Dashboard will carry that optional metadata through to a unique fold-based chart axis; old snapshots without dates remain readable and explicitly ordinal.

**Tech Stack:** Python 3.11+, pandas, JSON Schema, research-core adapters, React/TypeScript, Node test runner, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-08-30-niu-men-calendar-aware-folds-design.md`

## Global Constraints

- Do not infer dates from `foldId`, snapshot generated date, or bar counts.
- Do not present a mixed per-symbol date range as one unified full-market backtest interval.
- Keep `niu_men.research_snapshot.v2` and `trading_research.strategy_snapshot.v1` backward compatible.
- Old snapshots without date metadata must remain loadable and visibly marked as ordinal windows.
- Do not change existing OOS metric calculations or force variants from different strategies to align.
- Every production behavior change gets a failing regression test before implementation.

---

### Task 1: Specify and test fold calendar aggregation

**Files:**
- Modify: `packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py`
- Test: `packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py`

**Interfaces:**
- Consumes: existing `_write_snapshot_inputs`, `build_snapshot`, and `folds.csv` fixture rows.
- Produces: expected `walkForward.summaries[*].calendar` shape for exporter implementation.

- [ ] **Step 1: Write failing tests for exact, range, and unknown dates**

Extend the fixture helper with optional `test_start` and `test_end` values on fold rows. Add three tests:

```python
def test_export_dashboard_snapshot_emits_exact_calendar_metadata(tmp_path: Path) -> None:
    _write_snapshot_inputs(tmp_path, fold_dates=[("2024-01-02", "2024-12-31")])
    snapshot = _run_export(tmp_path)
    calendar = snapshot["walkForward"]["summaries"][0]["calendar"]
    assert calendar == {
        "mode": "exact",
        "startDate": "2024-01-02",
        "endDate": "2024-12-31",
        "datedSymbols": 2,
        "totalSymbols": 2,
        "distinctDatePairs": 1,
    }
```

Use a second fixture with two symbols and different date pairs and assert `mode == "range"`,
`startDateMin`, `startDateMax`, `endDateMin`, `endDateMax`, `datedSymbols`, `totalSymbols`, and
`distinctDatePairs`. Use the existing no-date fixture and assert `mode == "unknown"` with only
`datedSymbols == 0`, `totalSymbols == 2`, and `distinctDatePairs == 0`.

- [ ] **Step 2: Run the focused tests and confirm the expected failure**

Run from the repository root:

```bash
uv run --locked --package niu-men-line-strategy --extra dev \
  python -m pytest -q packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py
```

Expected: the new tests fail because `_rolling_summaries` does not yet emit `calendar`.

- [ ] **Step 3: Commit the red tests**

```bash
git add packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py
git commit -m "test: specify Niu Men fold calendar metadata"
```

### Task 2: Implement exporter calendar metadata and schema support

**Files:**
- Modify: `packages/niu-men-line-strategy/scripts/export_dashboard_snapshot.py`
- Modify: `packages/niu-men-line-strategy/schemas/research-snapshot.schema.json`
- Modify: `apps/dashboard/schemas/research-snapshot.schema.json`
- Modify: `packages/research-core/src/research_core/schemas/research-snapshot.schema.json`
- Test: `packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py`

**Interfaces:**
- Consumes: `folds` DataFrame columns `fold_id`, `symbol`, `test_start`, `test_end`.
- Produces: `_fold_calendar(folds, fold_id) -> dict[str, Any]` and optional `calendar` on each
  v2 rolling summary.

- [ ] **Step 1: Implement the smallest calendar aggregation helper**

Add a helper that filters one `fold_id`, parses `test_start` and `test_end` with coercion, and
keeps only rows with both valid ISO dates. Return:

```python
{
    "mode": "unknown",
    "datedSymbols": 0,
    "totalSymbols": total_symbols,
    "distinctDatePairs": 0,
}
```

when the fold has no valid pairs. For valid rows, deduplicate by symbol, compute `distinctDatePairs`,
and return `exact` only when every fold symbol is dated and all pairs match. Otherwise return `range`
with min/max start/end dates and the counts. Do not use summary CSV rows for this aggregation because
the summary is already grouped by variant/fold and does not retain symbol-level date coverage.

- [ ] **Step 2: Attach metadata while exporting summaries**

Change `_rolling_summaries(summary, folds)` to look up calendar metadata by `fold_id`, and call it
from `build_snapshot` with the loaded folds DataFrame. Keep the existing metric fields unchanged and
add `record["calendar"]` to every emitted summary, including unknown metadata.

- [ ] **Step 3: Extend the v2 rolling-summary schemas**

Add an optional `calendar` property to the `rollingSummary` definition in all three mirrored schema
files. Define a closed `calendarMetadata` object with:

- required `mode`, `datedSymbols`, `totalSymbols`, `distinctDatePairs`;
- `mode` enum `exact`, `range`, `unknown`;
- ISO date properties `startDate`, `endDate`, `startDateMin`, `startDateMax`, `endDateMin`, `endDateMax`;
- non-negative integer counts;
- `additionalProperties: false`.

The schema should allow exact objects to contain exact dates and range objects to contain min/max
dates; semantic mode/date consistency remains enforced by the exporter tests.

- [ ] **Step 4: Run exporter tests and the package schema tests**

```bash
uv run --locked --package niu-men-line-strategy --extra dev \
  python -m pytest -q packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py
uv run --locked --package research-core --dev \
  python -m pytest -q packages/research-core/tests/test_strategy_snapshot.py
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit the exporter and schema change**

```bash
git add packages/niu-men-line-strategy/scripts/export_dashboard_snapshot.py \
  packages/niu-men-line-strategy/schemas/research-snapshot.schema.json \
  apps/dashboard/schemas/research-snapshot.schema.json \
  packages/research-core/src/research_core/schemas/research-snapshot.schema.json \
  packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py
git commit -m "feat: preserve Niu Men fold calendar evidence"
```

### Task 3: Preserve calendar metadata through the generic research adapter

**Files:**
- Modify: `packages/research-core/src/research_core/adapters.py`
- Modify: `packages/research-core/src/research_core/schemas/strategy-snapshot.v1.schema.json`
- Modify: `apps/dashboard/web/src/research/genericSnapshot.ts`
- Modify: `apps/dashboard/web/src/research/strategySnapshot.ts`
- Test: `packages/research-core/tests/test_strategy_snapshot.py`
- Test: `apps/dashboard/web/src/genericSnapshot.test.mjs`

**Interfaces:**
- Consumes: v2 `rollingSummary.calendar` objects.
- Produces: generic v1 summaries carrying the same optional `calendar` object, and typed
  `StrategyRollingSummary.calendar` for frontend labels.

- [ ] **Step 1: Add failing adapter and parser assertions**

Add a calendar object to the generic Niu Men fixture summary and assert that
`adapt_niu_men_v2` preserves it. Add a frontend fixture assertion that `parseStrategyEnvelope`
and `envelopeToStrategySnapshot` preserve `calendar.mode === "range"`.

- [ ] **Step 2: Run the focused tests and confirm they fail**

```bash
uv run --locked --package research-core --dev \
  python -m pytest -q packages/research-core/tests/test_strategy_snapshot.py
npm --prefix apps/dashboard/web test -- --test-name-pattern="generic envelope|registry resolves"
```

Expected: the new assertions fail because adapters and TypeScript normalization currently discard
calendar metadata.

- [ ] **Step 3: Implement typed pass-through**

Add a shared `CalendarMetadata` shape to the generic adapter/schema and copy the optional property
from v2 summaries into generic summaries. Extend `GenericEnvelope.walkForward.summaries`,
`StrategyRollingSummary`, `RollingLabelInput`, `asOptionalDate` validation, and `toSummaries` so
the metadata is validated and retained without changing the generic schema version.

- [ ] **Step 4: Run focused tests and commit**

```bash
uv run --locked --package research-core --dev \
  python -m pytest -q packages/research-core/tests/test_strategy_snapshot.py
npm --prefix apps/dashboard/web test -- --test-name-pattern="generic envelope|registry resolves"
git add packages/research-core/src/research_core/adapters.py \
  packages/research-core/src/research_core/schemas/strategy-snapshot.v1.schema.json \
  apps/dashboard/web/src/research/genericSnapshot.ts \
  apps/dashboard/web/src/research/strategySnapshot.ts \
  packages/research-core/tests/test_strategy_snapshot.py \
  apps/dashboard/web/src/genericSnapshot.test.mjs
git commit -m "feat: carry fold calendar metadata through adapters"
```

### Task 4: Render unique date-aware Niu Men chart axes

**Files:**
- Modify: `apps/dashboard/web/src/research/rollingLabels.ts`
- Modify: `apps/dashboard/web/src/components/ResearchPanel.tsx`
- Modify: `apps/dashboard/web/src/chartVisuals.test.mjs`
- Modify: `apps/dashboard/web/src/genericSnapshot.test.mjs`

**Interfaces:**
- Consumes: `StrategyRollingSummary` with exact/range/unknown calendar metadata.
- Produces: one x-axis coordinate per `foldId`, labels using exact dates, date ranges, or ordinal
  fallback, with all variants aligned by `(variant, foldId)`.

- [ ] **Step 1: Add failing label and unique-fold tests**

Add tests asserting:

```ts
rollingSummaryLabel({
  foldId: 0,
  calendar: {
    mode: 'range',
    startDateMin: '2019-03-01',
    endDateMax: '2021-02-28',
    datedSymbols: 3500,
    totalSymbols: 3808,
    distinctDatePairs: 12,
  },
}) === '2019-03-01 → 2021-02-28（个股日期范围）';
```

Add a source-level assertion that the chart derives x-axis summaries from unique fold IDs rather
than `snapshot.rollingSummaries` directly.

- [ ] **Step 2: Run the focused frontend tests and confirm failure**

```bash
npm --prefix apps/dashboard/web test -- --test-name-pattern="rolling summary labels|research panel"
```

Expected: range metadata is ignored and the chart source still maps duplicate summary rows.

- [ ] **Step 3: Implement date-aware labels and unique fold alignment**

Update `rollingSummaryLabel` to use exact dates first, then range metadata, then ordinal fallback.
In `ResearchPanel`, create one sorted summary per fold for the x-axis and use fold IDs as the
variant map key. Keep the existing date-aware behavior for R-Breaker and ICT and the explicit
ordinal note for old Niu Men data.

- [ ] **Step 4: Run frontend tests and build**

```bash
npm --prefix apps/dashboard/web test
npm --prefix apps/dashboard/web run build
```

Expected: all frontend tests pass and TypeScript compilation succeeds.

- [ ] **Step 5: Commit the chart behavior**

```bash
git add apps/dashboard/web/src/research/rollingLabels.ts \
  apps/dashboard/web/src/components/ResearchPanel.tsx \
  apps/dashboard/web/src/chartVisuals.test.mjs \
  apps/dashboard/web/src/genericSnapshot.test.mjs
git commit -m "fix: align rolling charts to unique calendar folds"
```

### Task 5: Validate migration behavior and document release evidence

**Files:**
- Modify: `apps/dashboard/docs/contextual-research.md`
- Modify: `packages/niu-men-line-strategy/docs/dashboard-snapshot.md`
- Test: `packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py`

**Interfaces:**
- Consumes: exporter output with calendar metadata and legacy output without it.
- Produces: documented release procedure and explicit migration checks.

- [ ] **Step 1: Add a regression assertion for legacy snapshots**

Keep the existing no-date fixture and assert it still validates and produces `calendar.mode ==
"unknown"`; this prevents the new optional field from breaking old artifacts.

- [ ] **Step 2: Document the release check**

Document that a new OOS run must publish fold rows with `test_start` and `test_end`, then run the
exporter and inspect `research.json.walkForward.summaries[*].calendar`. State that the currently
checked-in snapshot cannot gain truthful dates without rerunning/exporting from those artifacts.

- [ ] **Step 3: Run the full repository verification**

```bash
export TMPDIR=/path/to/user/code/.task-tmp
uv run --locked --package niu-men-line-strategy --extra dev python -m pytest -q packages/niu-men-line-strategy/tests
uv run --locked --package research-core --dev python -m pytest -q packages/research-core/tests
ruff check packages/niu-men-line-strategy/scripts packages/niu-men-line-strategy/tests \
  packages/research-core/src/research_core packages/research-core/tests
npm --prefix apps/dashboard/web test
npm --prefix apps/dashboard/web run build
python apps/dashboard/scripts/validate_static_assets.py --require-contextual
git diff --check
```

- [ ] **Step 4: Commit documentation and final verification evidence**

```bash
git add apps/dashboard/docs/contextual-research.md \
  packages/niu-men-line-strategy/docs/dashboard-snapshot.md \
  packages/niu-men-line-strategy/tests/test_export_dashboard_snapshot.py
git commit -m "docs: document Niu Men calendar-aware snapshot release"
```

After a real OOS artifact with date-bearing fold rows is available, regenerate `research.json`, run
the same validation commands, deploy the Worker, and verify the live snapshot contains `calendar`.
