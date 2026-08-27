# Alpaca US Historical Bars Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed Alpaca US historical bar provider for daily and one-minute equities data without exposing Alpaca credentials to the browser.

**Architecture:** Extend `market-data-service` with a canonical `Bar`/`BarTimeframe` contract and an `AlpacaHistoricalProvider`. The provider accepts the existing `AlpacaConfig`, normalizes US symbols through the existing instrument model, builds `StockBarsRequest` objects with the configured feed and corporate-action adjustment, executes the synchronous SDK call off the async event loop, and maps Alpaca bars into provider-neutral `Bar` records. Dashboard/network wiring is a separate step after this provider contract is stable.

**Tech Stack:** Python 3.11+, alpaca-py 0.44.x, asyncio, pytest

**Spec:** Extends `docs/superpowers/specs/2026-08-27-hk-us-market-support-design.md` beyond its original realtime-only US scope.

## Global Constraints

- Credentials remain server-side only.
- Only US symbols are accepted by the Alpaca historical provider.
- Initial historical timeframes are `1d` and `1m`.
- Returned timestamps are timezone-aware.
- Empty Alpaca responses return an empty list, not fabricated bars.
- Provider tests use injected clients and no live network.
- Realtime Alpaca behavior remains unchanged.

---

### Task 1: Add canonical historical bar contract

- [ ] Add failing contract assertions for `Bar` and `BarTimeframe`.
- [ ] Implement validation for symbol, OHLC, volume and timezone-aware timestamp.
- [ ] Run focused contract tests green.

### Task 2: Add Alpaca historical provider

- [ ] Add failing tests for daily/minute request mapping, feed propagation and symbol normalization.
- [ ] Implement `AlpacaHistoricalProvider.fetch_bars()` using `StockHistoricalDataClient.get_stock_bars()` through `asyncio.to_thread`.
- [ ] Map Alpaca bar objects to canonical `Bar` records.
- [ ] Run focused tests green.

### Task 3: Error and empty-result behavior

- [ ] Add tests for non-US rejection and empty bar sets.
- [ ] Preserve SDK/provider errors for callers to classify; do not fabricate fallback data inside the provider.
- [ ] Run focused tests green.

### Task 4: Integration gate

- [ ] Run the complete market-data-service pytest/Ruff suite in a real checkout.
- [ ] Keep the existing alpaca-py version range and regenerate/check the root lock only if dependency metadata changes.
- [ ] Open a dedicated provider PR; Dashboard historical consumption follows separately.
