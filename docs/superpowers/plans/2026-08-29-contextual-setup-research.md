# Contextual Setup Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有行情和 strategy snapshot contract 的前提下，为 Dashboard 增加可复用的市场上下文、setup event、day archetype、intermarket 和 event study 研究层。

**Architecture:** `research-core` 提供版本化 JSON Schema 与 Python validator；Dashboard Python 从现有 `StockData` 语义派生 contextual snapshot；React 只解析并展示生成结果。所有新增字段保持 optional，旧 `data.json` 和旧 producer 不需要迁移。

**Tech Stack:** Python 3.11、pandas、numpy、jsonschema、React、TypeScript、Vite、Node test runner。

**Spec:** `docs/superpowers/specs/2026-08-29-contextual-setup-research-design.md`

## Global Constraints

- 不改变 `trading_research.strategy_snapshot.v1`。
- 不实现 ICT 交易策略或主观 confluence score。
- 不新增经济日历第三方 provider；event study 只消费标准化事件输入。
- 不提交原始 minute bars、大型 OOS 产物或凭据。
- `contextualResearch` 必须 optional；缺失或局部失败不得阻断现有 Dashboard。
- session 按 `market + timezone` 定义，不把教材中的固定 EST 时间硬编码到所有市场。
- 检测结果必须是可观察事实，并包含 definition version/provenance。

---

### Task 1: Research Core Context Contracts

**Files:**
- Create: `packages/research-core/src/research_core/schemas/market-context.v1.schema.json`
- Create: `packages/research-core/src/research_core/schemas/setup-event.v1.schema.json`
- Create: `packages/research-core/src/research_core/schemas/event-study.v1.schema.json`
- Create: `packages/research-core/src/research_core/schemas/contextual-snapshot.v1.schema.json`
- Create: `packages/research-core/src/research_core/contextual.py`
- Modify: `packages/research-core/src/research_core/__init__.py`
- Create: `packages/research-core/tests/test_contextual.py`
- Modify: `packages/research-core/README.md`

**Interfaces:**
- Produces constants: `MARKET_CONTEXT_VERSION`, `SETUP_EVENT_VERSION`, `EVENT_STUDY_VERSION`, `CONTEXTUAL_SNAPSHOT_VERSION`.
- Produces validators: `validate_market_context()`, `validate_setup_event()`, `validate_event_study()`, `validate_contextual_snapshot()`.
- Produces loader: `load_contextual_snapshot(path: str | Path) -> dict[str, Any]`.

- [ ] **Step 1: Write failing validator tests**

Test valid minimal envelopes and invalid missing required fields. Example:

```python
from research_core.contextual import (
    CONTEXTUAL_SNAPSHOT_VERSION,
    MARKET_CONTEXT_VERSION,
    SETUP_EVENT_VERSION,
    validate_contextual_snapshot,
    validate_market_context,
    validate_setup_event,
)


def test_market_context_requires_instrument():
    payload = {
        "schemaVersion": MARKET_CONTEXT_VERSION,
        "dataDate": "2026-08-28",
        "market": "US",
        "timezone": "America/New_York",
        "referenceLevels": [],
        "sessions": [],
        "dayArchetype": {"id": "range", "reasons": []},
        "features": {},
        "intermarket": [],
        "provenance": {"source": "dashboard-data-json"},
    }
    with pytest.raises(ValueError, match="instrument"):
        validate_market_context(payload)
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `uv run --package research-core pytest packages/research-core/tests/test_contextual.py -q`

Expected: FAIL because `research_core.contextual` does not exist.

- [ ] **Step 3: Add four schemas and generic validator helper**

`contextual.py` uses `importlib.resources.files("research_core.schemas")` and `Draft202012Validator`, matching `strategy_snapshot.py`. Keep each public validator small and route through:

```python
def _validate(kind: str, validator: Draft202012Validator, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{kind} validation failed: root must be an object")
    errors = sorted(validator.iter_errors(payload), key=_error_sort_key)
    if errors:
        error = errors[0]
        raise ValueError(f"{kind} validation failed at {_error_location(error)}: {error.message}")
```

`contextual-snapshot.v1` requires `schemaVersion/generatedAt/dataDate/quality/coverage/contexts/setupEvents/eventStudies/provenance`; nested arrays reference the other schemas through local `$defs` copies or equivalent self-contained definitions so package-resource validation does not depend on network resolution.

- [ ] **Step 4: Export public API and document ownership**

Update `research_core.__init__` and README to state these contracts are strategy-independent observational research contracts.

- [ ] **Step 5: Run research-core tests and lint**

Run:

```bash
uv run --package research-core pytest packages/research-core/tests -q
uv run --package research-core ruff check packages/research-core/src packages/research-core/tests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/research-core
git commit -m "feat: add contextual research contracts"
```

---

### Task 2: Session, Reference Level, Day Archetype, and Outcome Engine

**Files:**
- Create: `apps/dashboard/src/trading_research/dashboard/contextual_research.py`
- Create: `apps/dashboard/tests/test_contextual_research.py`

**Interfaces:**
- Produces `semantic_reference_levels(stock: Mapping[str, Any]) -> list[dict[str, Any]]`.
- Produces `session_for_timestamp(timestamp: str | pd.Timestamp, market: str, timezone: str) -> str | None`.
- Produces `classify_day_archetype(stock: Mapping[str, Any]) -> dict[str, Any]`.
- Produces `build_market_context(stock: Mapping[str, Any], *, data_date: str) -> dict[str, Any]`.
- Produces `detect_setup_events(stock: Mapping[str, Any], context: Mapping[str, Any]) -> list[dict[str, Any]]`.

- [ ] **Step 1: Write failing session/reference tests**

Cover exact US/CN/HK boundaries and semantic levels from `indicators` + existing `levels`. Example expectations:

```python
assert session_for_timestamp("2026-08-28 09:45:00", "US", "America/New_York") == "opening_range"
assert {level["kind"] for level in semantic_reference_levels(stock)} >= {
    "previous_day_high", "previous_day_low", "opening_range_high", "opening_range_low", "vwap"
}
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `uv run --package trading-research-dashboard-app pytest apps/dashboard/tests/test_contextual_research.py -q`

Expected: FAIL because module/functions do not exist.

- [ ] **Step 3: Implement session configuration and level derivation**

Use data-only `SESSION_WINDOWS` with `datetime.time` boundaries. `semantic_reference_levels()` de-duplicates by `(kind, rounded value)` and computes `distancePct` against the latest intraday price when available, otherwise `lastClose`.

- [ ] **Step 4: Add day archetype tests first**

Fixtures cover `trend_up`, `trend_down`, `range`, `opening_drive_up`, `opening_drive_down`, `morning_reversal`, `late_breakout`, and `insufficient_data`. Every result must include non-empty `reasons` except `insufficient_data`, which states the missing requirement.

- [ ] **Step 5: Implement transparent archetype rules**

Use only current data fields:

```python
range_to_atr = (day_high - day_low) / atr20 if atr20 else None
close_location = (close - day_low) / (day_high - day_low) if day_high > day_low else 0.5
```

Prefer opening-drive rules when ORB break and close location agree; otherwise trend rules for `range_to_atr >= 1.0` and extreme close location; reversal when morning extreme occurs early and close finishes opposite; late breakout when HOD/LOD first occurs in final configured session; default to `range`.

- [ ] **Step 6: Add setup detector and outcome tests first**

Use a deterministic intraday sequence around a known reference level and assert:

```python
assert event["eventType"] == "reclaim_below"
assert event["outcome"]["return5m"] == pytest.approx(...)
assert event["outcome"]["mfe30m"] >= 0
assert event["outcome"]["mae30m"] <= 0
```

- [ ] **Step 7: Implement setup detector**

Definition version: `setup-detector.v1`.

Rules use bar-close price and a tolerance of `max(abs(level) * 0.0005, atr20 * 0.02)` when ATR is present. `reclaim_below` means price traded above level then returned below within 3 subsequent bars; `reclaim_above` is symmetric. `break_and_hold_*` requires 3 consecutive closes beyond level. `reject_*` requires cross beyond level followed by immediate close back on the original side. Compute forward outcomes using available bars nearest to +5/+15/+30 minutes and extrema through +30 minutes.

- [ ] **Step 8: Run focused tests**

Run: `uv run --package trading-research-dashboard-app pytest apps/dashboard/tests/test_contextual_research.py -q`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/dashboard/src/trading_research/dashboard/contextual_research.py apps/dashboard/tests/test_contextual_research.py
git commit -m "feat: derive market context and setup events"
```

---

### Task 3: Intermarket and Event Study Research

**Files:**
- Create: `apps/dashboard/src/trading_research/dashboard/intermarket.py`
- Create: `apps/dashboard/src/trading_research/dashboard/event_study.py`
- Create: `apps/dashboard/tests/test_intermarket.py`
- Create: `apps/dashboard/tests/test_event_study.py`

**Interfaces:**
- Produces `build_intermarket_observations(stocks: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]` keyed by instrument code.
- Produces `build_event_studies(stock: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]`.

- [ ] **Step 1: Write failing intermarket tests**

Create two 25-bar daily series with known correlated returns and a final new-high divergence. Assert `correlation20`, `relativeStrength20`, `extremeConfirmation`, and `relativeExtremeDivergence`.

- [ ] **Step 2: Implement intermarket observations**

Join daily closes by date, require at least 20 overlapping bars, calculate percentage returns with pandas, and choose peer pairs only within the available snapshot. No fixed “NVDA must use SMH” mapping is required in v1; compare each instrument against the most correlated eligible peer and record the peer code.

- [ ] **Step 3: Write failing event-study tests**

Use a normalized input event:

```python
{
    "id": "fomc-2026-07-29",
    "category": "FOMC",
    "importance": "high",
    "timestamp": "2026-07-29 14:00:00",
}
```

Assert pre-event return/range, immediate range, +15/+30/+60m returns, MFE/MAE, and initial move reversal when data supports it.

- [ ] **Step 4: Implement event studies**

Only consume provided events. Ignore events outside the stock intraday date or timezone-normalized window. Return standalone `trading_research.event_study.v1` envelopes with `source="provided-event-input"` provenance.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run --package trading-research-dashboard-app pytest \
  apps/dashboard/tests/test_intermarket.py \
  apps/dashboard/tests/test_event_study.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/src/trading_research/dashboard/intermarket.py \
  apps/dashboard/src/trading_research/dashboard/event_study.py \
  apps/dashboard/tests/test_intermarket.py \
  apps/dashboard/tests/test_event_study.py
git commit -m "feat: add intermarket and event studies"
```

---

### Task 4: Generate Optional Contextual Snapshot in data.json

**Files:**
- Modify: `apps/dashboard/src/trading_research/dashboard/contextual_research.py`
- Modify: `apps/dashboard/src/trading_research/dashboard/astock_tech.py`
- Modify: `apps/dashboard/tests/test_cli.py`
- Create: `apps/dashboard/tests/test_contextual_snapshot.py`

**Interfaces:**
- Produces `build_contextual_snapshot(stocks: Sequence[Mapping[str, Any]], *, generated_at: str, events: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]`.
- `astock_tech.main(..., contextual_events: Sequence[Mapping[str, Any]] | None = None)` writes `{generatedAt, stocks, contextualResearch}`.

- [ ] **Step 1: Write failing snapshot integration test**

Assert generated snapshot has:

```python
assert snapshot["schemaVersion"] == "trading_research.contextual_snapshot.v1"
assert snapshot["contexts"][0]["schemaVersion"] == "trading_research.market_context.v1"
assert snapshot["quality"]["status"] in {"pass", "warning"}
```

and passes `research_core.validate_contextual_snapshot(snapshot)`.

- [ ] **Step 2: Implement snapshot assembly**

Build all per-stock contexts first, then inject intermarket observations, then setup events, then optional event studies. Coverage includes `requested/evaluated/skipped`. Any per-stock exception appends a warning and increments `skipped`; do not fail the whole dashboard.

- [ ] **Step 3: Integrate with `astock_tech.main`**

When `json_path` is supplied:

```python
dashboard = {
    "generatedAt": last_trade_day_str,
    "stocks": payloads,
    "contextualResearch": build_contextual_snapshot(
        payloads,
        generated_at=last_trade_day_str,
        events=contextual_events,
    ),
}
```

If no stocks exist, preserve current empty behavior and emit a valid empty contextual snapshot only when JSON is written.

- [ ] **Step 4: Run dashboard Python tests**

Run: `uv run --package trading-research-dashboard-app pytest apps/dashboard/tests -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/dashboard/src/trading_research/dashboard apps/dashboard/tests
git commit -m "feat: publish contextual research with dashboard data"
```

---

### Task 5: Frontend Contextual Research Panel

**Files:**
- Modify: `apps/dashboard/web/src/types.ts`
- Create: `apps/dashboard/web/src/contextualResearch.ts`
- Create: `apps/dashboard/web/src/contextualResearch.test.mjs`
- Create: `apps/dashboard/web/src/components/ContextualResearchPanel.tsx`
- Create: `apps/dashboard/web/src/components/ContextualResearchPanel.test.mjs`
- Modify: `apps/dashboard/web/src/components/SelectedInstrumentWorkspace.tsx`
- Modify: `apps/dashboard/web/src/editorial.css`
- Modify: `apps/dashboard/web/tests/e2e/dashboard.spec.mjs`

**Interfaces:**
- Adds `contextualResearch?: ContextualResearchSnapshot` to `DashboardData`.
- Produces `parseContextualResearch(value: unknown): ContextualResearchSnapshot | null`.
- `SelectedInstrumentWorkspace` accepts optional `contextualResearch` and passes the matching context/events/studies into `ContextualResearchPanel`.

- [ ] **Step 1: Write failing parser tests**

Cover valid minimal snapshot, unsupported version, malformed arrays, and absent value. Parser returns `null` for invalid/unsupported input rather than throwing and breaking the page.

- [ ] **Step 2: Add TypeScript models and parser**

Model semantic reference levels, session summaries, day archetype, setup outcomes, intermarket observations, event studies, quality and coverage. Keep wire names identical to Python/schema names.

- [ ] **Step 3: Write failing panel rendering tests**

Use `renderToStaticMarkup` or the repository's existing lightweight component test pattern. Assert labels for `日型`, `参考价位`, `Setup 事件`, `跨市场确认`, and empty-state behavior.

- [ ] **Step 4: Implement `ContextualResearchPanel`**

Render no confluence score. Show sample factual metrics: archetype + reasons, range/ATR, reference level distance, recent setup outcome, peer correlation/divergence, and event study rows only when present.

- [ ] **Step 5: Wire panel into selected instrument workspace**

Update caller(s) to pass Dashboard-level contextual snapshot. If snapshot is absent or parser returns null, existing workspace markup remains unchanged except for no contextual panel.

- [ ] **Step 6: Add responsive styling and E2E assertions**

Use existing editorial tokens; no new palette. Verify mobile viewport has no horizontal overflow and contextual panel can render with fixture data.

- [ ] **Step 7: Run frontend tests/build**

Run:

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/dashboard/web
git commit -m "feat: show contextual setup research"
```

---

### Task 6: Documentation, Regression, and PR Verification

**Files:**
- Modify: `apps/dashboard/docs/outputs.md`
- Modify: `apps/dashboard/docs/indicators.md`
- Modify: `apps/dashboard/docs/web-frontend.md`
- Modify: `docs/roadmap/README.md`
- Modify: `docs/superpowers/specs/2026-08-29-contextual-setup-research-design.md` only if implementation reveals a material contract correction.

**Interfaces:** None; documentation must describe only verified behavior.

- [ ] **Step 1: Update docs from implemented behavior**

Document `contextualResearch`, supported semantic levels/session definitions/setup event definitions/day archetypes/intermarket behavior and external event-input boundary. Explicitly state that existing committed demo `data.json` may predate the optional field until regenerated.

- [ ] **Step 2: Run targeted contract sync/foundation tests**

Run:

```bash
uv run pytest -q \
  packages/research-core/tests \
  apps/dashboard/tests \
  tests/test_foundation.py \
  tests/test_research_contract_sync.py
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

Expected: PASS.

- [ ] **Step 3: Review branch diff**

Check for credentials, raw market data, generated build artifacts, unrelated refactors, placeholder comments and accidental changes to `research.json`/`rbreaker-research.json`.

- [ ] **Step 4: Commit documentation**

```bash
git add apps/dashboard/docs docs/roadmap docs/superpowers
git commit -m "docs: document contextual setup research"
```

- [ ] **Step 5: Open PR**

PR title: `feat: add contextual setup research layer`

PR body must summarize contracts, detector semantics, frontend changes, compatibility, validation evidence, and known boundary that no external economic-calendar provider is included.
