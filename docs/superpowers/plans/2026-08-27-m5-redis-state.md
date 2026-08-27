# M5 Redis State Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Redis latest-quote, heartbeat and Pub/Sub state layer required by M5 while preserving the existing in-memory store until API wiring is migrated separately.

**Architecture:** Introduce `market_data_service.redis_state.RedisQuoteStore` behind a small async Redis-client protocol so unit tests require no real Redis. Store canonical normalized quote JSON under the frozen M5 namespace, reject older writes, publish accepted quotes through the fixed channel, reclassify freshness at read time, and store collector heartbeat with a finite TTL. A later wiring task will switch collector/API/WebSocket consumers to this state layer.

**Tech Stack:** Python 3.11+, asyncio, redis-py asyncio runtime dependency, pytest

**Spec:** `docs/superpowers/specs/2026-08-26-m5-live-market-data-runtime-design.md`

## Global Constraints

- Redis keys remain `trading-research:live:v1:quote:<symbol>` and `trading-research:live:v1:collector:heartbeat`.
- Pub/Sub channel remains `trading-research:live:v1:quotes`.
- Latest quote keys do not receive a short TTL.
- Heartbeat uses a finite configurable TTL.
- A write older than the current stored quote is rejected.
- Freshness is recomputed at read time.
- Unit tests do not require a real Redis server.
- Existing synchronous in-memory `QuoteStore` remains available until network wiring is migrated.

---

### Task 1: Establish Redis state module boundary

- [ ] Add a failing module-boundary test.
- [ ] Create `redis_state.py` with namespace constants and client protocol.
- [ ] Run the focused test green.

### Task 2: Quote codec and latest-state behavior

- [ ] Add tests for normalized UTC serialization, missing reads, current/stale reads, and monotonic writes.
- [ ] Implement quote encode/decode and `get_quote` / `put_quote`.
- [ ] Run focused tests green.

### Task 3: Pub/Sub behavior

- [ ] Add tests that accepted quotes publish on the fixed channel and subscriptions filter requested symbols.
- [ ] Implement `publish_quote` and async subscription context manager.
- [ ] Run focused tests green.

### Task 4: Collector heartbeat

- [ ] Add heartbeat roundtrip/TTL tests.
- [ ] Implement heartbeat codec/read/write.
- [ ] Run focused tests green.

### Task 5: Runtime dependency and integration gate

- [ ] Add `redis` runtime dependency to `apps/market-data-service/pyproject.toml`.
- [ ] Regenerate and check root `uv.lock` in a real checkout.
- [ ] Run market-data-service pytest/Ruff plus root foundation checks before marking the PR ready.
