# HK and US Market Support Implementation Plan

**Goal:** Add Hong Kong compatibility data adapters and server-side Alpaca US real-time quotes while preserving the static Dashboard fallback.

**Spec:** `docs/superpowers/specs/2026-08-27-hk-us-market-support-design.md`

**Branch:** `feat/hk-us-market-support`

## Constraints

- Existing CN stock/ETF behavior and old `data.json` snapshots remain compatible.
- Alpaca credentials stay server-side.
- HK minute data is delayed compatibility data and is never labeled live.
- No Redis, database, account/order APIs, or unrelated data-layer rewrite.
- `main` stays untouched.

## Implemented

- [x] Add market-aware `Market` / `Instrument` contracts and canonical CN/HK/US symbol parsing.
- [x] Preserve existing CN symbol aliases and reject ambiguous bare US tickers outside US-aware entry points.
- [x] Add `AlpacaConfig`, IEX/SIP/delayed-SIP feed mapping, `QuoteStore`, and freshness handling.
- [x] Add one shared `StockDataStream` collector with `data_timeout=60` and delayed/live status preservation.
- [x] Add FastAPI `GET /healthz`, `GET /v1/quotes/{symbol}`, and `WS /v1/stream` endpoints.
- [x] Add `market_compat` facade so CN/ETF calls retain their existing provider chain and function signatures.
- [x] Add HK AKShare daily/minute adapters with runtime-cache fallback.
- [x] Select HK previous trading day from HK daily bars instead of the A-share calendar.
- [x] Add `market`, `currency`, and `timezone` metadata to generated Dashboard payloads.
- [x] Remove the hard-coded cross-market `14:55` force-flat wording and use market-aware guidance.
- [x] Add optional US WebSocket live overlay in the SPA without mutating historical bars.
- [x] Fall back to static snapshot prices when live quotes become stale or the WebSocket is unavailable.
- [x] Keep research snapshot loading independent of quote ticks.
- [x] Document HK compatibility, Alpaca configuration, feed semantics, and `VITE_MARKET_DATA_URL` in allowed repository docs.
- [x] Review tracked-file boundaries and remove the temporary Dashboard doc that was outside the foundation allowlist.

## Focused verification completed

The local CodexPro workspace connection became unavailable during implementation, so the repository worktree could not be used for final end-to-end verification. Focused executable harnesses were run against the implemented contracts instead:

- [x] market-data service symbol/config/store/provider/API/collector harness: 12 passed.
- [x] HK compatibility facade harness: 5 passed.
- [x] market-aware generator helper harness: 3 passed.
- [x] frontend live-quote helper harness: 6 passed.
- [x] Current Alpaca SDK `StockDataStream.run()`, `stop()`, feed enum, and `data_timeout` behavior checked against official documentation/source.
- [x] PR diff reviewed for credentials, raw market data, local paths, and foundation allowlist violations.

## Required before the PR can leave Draft

- [ ] Create/use a real local worktree for `feat/hk-us-market-support` once the local repository connector is available again.
- [ ] Run `uv lock` and commit the regenerated root `uv.lock` for `alpaca-py`, FastAPI, uvicorn, and httpx.
- [ ] Run `uv run --package market-data-service pytest apps/market-data-service/tests`.
- [ ] Run `uv run --package market-data-service ruff check apps/market-data-service`.
- [ ] Run the full Dashboard Python test suite and Ruff checks.
- [ ] Run `npm test` and `npm run build` in `apps/dashboard/web`.
- [ ] Run root pytest and `uv run python scripts/check_foundation.py` (or the equivalent repository foundation workflow).
- [ ] Review the final lockfile/diff and only then convert PR #37 from Draft to Ready.

## Known scope boundary

This PR intentionally does not add complete US historical daily/minute bars to the Dashboard generator. The Alpaca work in this PR is the server-side real-time quote layer and SPA live overlay. A US instrument must already exist in the static Dashboard snapshot for the browser overlay to attach to it; pretending live ticks are a historical provider would make the contract simpler only in the same way removing brakes makes a car lighter.
