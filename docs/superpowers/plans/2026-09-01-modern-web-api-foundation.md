# Modern Web/API Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给现有 FastAPI 行情服务增加稳定 OpenAPI 契约，并让 React Dashboard 通过可测试的 REST client 感知行情服务状态，同时完整保留静态 JSON 降级模式。

**Architecture:** FastAPI endpoint 使用独立 Pydantic response models 声明 schema；前端新增纯函数 REST client，把 URL、HTTP 错误和 payload 校验集中处理。`App.tsx` 只消费 health 状态，不改变静态 dashboard/research 数据和现有 WebSocket overlay 的职责。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、pytest、React 19、TypeScript、Vite、Node test runner。

**Spec:** `docs/superpowers/specs/2026-09-01-modern-web-api-foundation-design.md`

## Global Constraints

- 保持 `niu_men.research_snapshot.v2` 兼容。
- 不提交原始行情、完整 OOS CSV、凭据、本机路径或大型回测产物。
- 不改变 GitHub Actions 的 `workflow_dispatch` only 策略。
- Dashboard 静态 `data.json` 与研究 snapshot 继续作为可部署、可降级的数据入口。
- 不在本 PR 引入 PostgreSQL、pnpm、Tailwind 或 shadcn 依赖。
- WebSocket `/v1/stream` payload 和 reconnect/stale 行为保持兼容。

---

### Task 1: Give FastAPI REST endpoints typed OpenAPI responses

**Files:**
- Create: `apps/market-data-service/src/market_data_service/api_models.py`
- Create: `apps/market-data-service/tests/test_openapi_contract.py`
- Modify: `apps/market-data-service/src/market_data_service/app.py`

**Interfaces:**
- Consumes: `QuoteStatus`, `Freshness`, `BarTimeframe` from `market_data_service.contracts`.
- Produces: `HealthResponse`, `ReadyResponse`, `QuoteResponse`, `BarResponse`, `BarsResponse` Pydantic models; named schemas in `create_app().openapi()`.

- [ ] **Step 1: Write the failing OpenAPI contract test**

```python
from market_data_service.app import create_app


def test_openapi_exposes_named_market_data_response_models() -> None:
    schema = create_app().openapi()
    components = schema["components"]["schemas"]

    assert "QuoteResponse" in components
    assert "BarsResponse" in components
    assert (
        schema["paths"]["/v1/quotes/{symbol}"]["get"]["responses"]["200"]["content"]
        ["application/json"]["schema"]["$ref"]
        == "#/components/schemas/QuoteResponse"
    )
    assert (
        schema["paths"]["/v1/bars/{symbol}"]["get"]["responses"]["200"]["content"]
        ["application/json"]["schema"]["$ref"]
        == "#/components/schemas/BarsResponse"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/market-data-service
uv run --locked pytest -q tests/test_openapi_contract.py
```

Expected: FAIL because the current endpoints expose anonymous object schemas and `QuoteResponse` / `BarsResponse` do not exist.

- [ ] **Step 3: Add minimal Pydantic response models**

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .contracts import BarTimeframe, Freshness, QuoteStatus


class HealthResponse(BaseModel):
    status: Literal["ok"]
    collectorConfigured: bool
    liveDataConfigured: bool


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    redis: Literal["disabled", "ok", "unavailable"]
    collector: Literal["disabled", "configured", "healthy", "stale"]


class QuoteResponse(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    source: str
    status: QuoteStatus
    freshness: Freshness


class BarResponse(BaseModel):
    symbol: str
    timeframe: BarTimeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class BarsResponse(BaseModel):
    symbol: str
    timeframe: BarTimeframe
    bars: list[BarResponse]
```

- [ ] **Step 4: Attach response models to the existing endpoints**

Update decorators only; keep existing payload construction and error behavior:

```python
@app.get("/healthz", response_model=HealthResponse)
@app.get("/readyz", response_model=ReadyResponse)
@app.get("/v1/quotes/{symbol}", response_model=QuoteResponse)
@app.get("/v1/bars/{symbol}", response_model=BarsResponse)
```

- [ ] **Step 5: Run focused and service tests**

```bash
cd apps/market-data-service
uv run --locked pytest -q tests/test_openapi_contract.py
uv run --locked pytest -q
uv run --locked ruff check src tests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/market-data-service/src/market_data_service/api_models.py \
  apps/market-data-service/src/market_data_service/app.py \
  apps/market-data-service/tests/test_openapi_contract.py
git commit -m "feat: type market data API responses"
```

---

### Task 2: Add a testable frontend REST client and service-status UI

**Files:**
- Create: `apps/dashboard/web/src/marketDataApi.ts`
- Create: `apps/dashboard/web/src/marketDataApi.test.mjs`
- Modify: `apps/dashboard/web/src/App.tsx`

**Interfaces:**
- Consumes: `VITE_MARKET_DATA_URL`, browser `fetch`, FastAPI `/healthz` and `/v1/quotes/{symbol}`.
- Produces: `fetchMarketDataHealth(baseUrl, fetchImpl?)`, `fetchMarketDataQuote(baseUrl, symbol, fetchImpl?)`, `MarketDataHealth`, `MarketDataQuote`.

- [ ] **Step 1: Write failing URL and payload tests**

```javascript
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  fetchMarketDataHealth,
  fetchMarketDataQuote,
} from './marketDataApi.ts';

test('health client removes trailing slash before requesting healthz', async () => {
  let requested = '';
  const fetchImpl = async (url) => {
    requested = String(url);
    return new Response(JSON.stringify({
      status: 'ok',
      collectorConfigured: true,
      liveDataConfigured: true,
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  };

  const result = await fetchMarketDataHealth('https://market.example/', fetchImpl);

  assert.equal(requested, 'https://market.example/healthz');
  assert.equal(result.liveDataConfigured, true);
});

test('quote client URL-encodes the symbol', async () => {
  let requested = '';
  const fetchImpl = async (url) => {
    requested = String(url);
    return new Response(JSON.stringify({
      symbol: 'us:AAPL',
      price: 200,
      timestamp: '2026-09-01T00:00:00+00:00',
      source: 'test',
      status: 'live',
      freshness: 'current',
    }), { status: 200, headers: { 'content-type': 'application/json' } });
  };

  await fetchMarketDataQuote('https://market.example', 'AAPL.US', fetchImpl);
  assert.equal(requested, 'https://market.example/v1/quotes/AAPL.US');
});

test('health client rejects malformed payloads', async () => {
  const fetchImpl = async () => new Response(JSON.stringify({ status: 'ok' }), { status: 200 });

  await assert.rejects(
    fetchMarketDataHealth('https://market.example', fetchImpl),
    /invalid market data health payload/i,
  );
});
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
node --test apps/dashboard/web/src/marketDataApi.test.mjs
```

Expected: FAIL because `marketDataApi.ts` does not exist.

- [ ] **Step 3: Implement the minimal REST client**

The module must:

- strip trailing slashes from the base URL;
- throw on empty base URL;
- throw `Market data API request failed: HTTP <status>` for non-2xx responses;
- validate health and quote objects with small type guards;
- use `encodeURIComponent(symbol)` in quote URLs;
- default `fetchImpl` to global `fetch`.

- [ ] **Step 4: Run focused client tests**

```bash
node --test apps/dashboard/web/src/marketDataApi.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Integrate service status into `App.tsx`**

Add state:

```typescript
type MarketDataServiceStatus = 'static' | 'online' | 'unavailable';
const [marketDataServiceStatus, setMarketDataServiceStatus] =
  useState<MarketDataServiceStatus>('static');
```

When `VITE_MARKET_DATA_URL` is empty, keep `static`. When configured, call `fetchMarketDataHealth()` in an effect and set `online` or `unavailable`. Do not set the page-level `error` state from health failures.

Render the existing data-status element as:

```typescript
const serviceStatusLabel = marketDataServiceStatus === 'online'
  ? '行情服务在线'
  : marketDataServiceStatus === 'unavailable'
    ? '静态快照 · 行情服务不可用'
    : '静态快照';
```

- [ ] **Step 6: Run frontend regression tests and build**

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/dashboard/web/src/marketDataApi.ts \
  apps/dashboard/web/src/marketDataApi.test.mjs \
  apps/dashboard/web/src/App.tsx
git commit -m "feat: add typed market data REST client"
```

---

### Task 3: Add OpenAPI export tooling and update integration docs

**Files:**
- Create: `apps/market-data-service/src/market_data_service/openapi_export.py`
- Create: `apps/market-data-service/scripts/export_openapi.py`
- Create: `apps/market-data-service/tests/test_openapi_export.py`
- Modify: `apps/market-data-service/README.md`
- Modify: `apps/market-data-service/docs/dashboard-integration.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `create_app().openapi()`.
- Produces: deterministic UTF-8 JSON text via `render_openapi_json()` and CLI `python scripts/export_openapi.py [output]`.

- [ ] **Step 1: Write the failing export test**

```python
import json

from market_data_service.openapi_export import render_openapi_json


def test_render_openapi_json_contains_market_data_paths() -> None:
    schema = json.loads(render_openapi_json())

    assert schema["info"]["title"] == "Market Data Service"
    assert "/v1/quotes/{symbol}" in schema["paths"]
    assert "/v1/bars/{symbol}" in schema["paths"]
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
cd apps/market-data-service
uv run --locked pytest -q tests/test_openapi_export.py
```

Expected: FAIL because `openapi_export` does not exist.

- [ ] **Step 3: Implement deterministic rendering**

```python
from __future__ import annotations

import json

from .app import create_app


def render_openapi_json() -> str:
    return json.dumps(
        create_app().openapi(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
```

The CLI writes stdout when no path is passed and uses `Path.write_text(..., encoding="utf-8")` when an output path is supplied.

- [ ] **Step 4: Run export tests**

```bash
cd apps/market-data-service
uv run --locked pytest -q tests/test_openapi_export.py tests/test_openapi_contract.py
```

Expected: PASS.

- [ ] **Step 5: Update docs with the new contract workflow**

Document:

```bash
cd apps/market-data-service
uv run --locked python scripts/export_openapi.py /tmp/market-data-openapi.json
```

State explicitly that the exported schema is the input for a future OpenAPI-to-TypeScript generated client, while the current frontend client stays intentionally small and hand-validated.

Document frontend service-state behavior and retain the existing static snapshot fallback description.

- [ ] **Step 6: Run full relevant validation**

```bash
cd apps/market-data-service
uv run --locked pytest -q
uv run --locked ruff check src tests scripts

cd ../../
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
uv run --locked --extra dev pytest -q
uv run --locked python scripts/check_foundation.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/market-data-service/src/market_data_service/openapi_export.py \
  apps/market-data-service/scripts/export_openapi.py \
  apps/market-data-service/tests/test_openapi_export.py \
  apps/market-data-service/README.md \
  apps/market-data-service/docs/dashboard-integration.md \
  README.md
git commit -m "docs: document OpenAPI contract workflow"
```

---

## Final review

- [ ] Confirm no secret, raw market data, cache, virtualenv or generated large artifact is in the diff.
- [ ] Confirm static Dashboard remains usable with no `VITE_MARKET_DATA_URL`.
- [ ] Confirm WebSocket URL logic is unchanged.
- [ ] Confirm `/openapi.json` names `QuoteResponse` and `BarsResponse`.
- [ ] Confirm all new client failure paths degrade to static mode rather than page-level failure.
- [ ] Record any commands that could not be executed in the PR description instead of claiming they passed.
