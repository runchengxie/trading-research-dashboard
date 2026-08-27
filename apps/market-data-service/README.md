# Market Data Service

Provider-neutral market metadata and live quote service for the Trading Research Dashboard.

The service now owns the stable cross-market symbol boundary and the server-side Alpaca connection used by the Dashboard. Static Dashboard snapshots remain the fallback when the live service is not configured or temporarily unavailable.

## Supported symbol forms

The canonical forms are deliberately explicit so downstream code does not have to guess markets:

- China A-share: `sz300246` (`SZ.300246` and `300246.SZ` are accepted aliases).
- Hong Kong: `hk00700` (`HK.00700` and `00700.HK` are accepted aliases).
- United States: `us:AAPL` (`AAPL.US` is accepted as an alias; a bare `AAPL` is accepted only by US-aware parsing/API paths).

`Instrument` metadata includes market, provider symbol, currency, and timezone:

| Market | Currency | Timezone |
| --- | --- | --- |
| CN | CNY | `Asia/Shanghai` |
| HK | HKD | `Asia/Hong_Kong` |
| US | USD | `America/New_York` |

## Alpaca live quotes

Alpaca credentials stay in the market-data-service process. They must never be placed in `data.json`, the Vite environment, or the browser bundle.

Required environment variables when the collector is enabled:

```bash
export APCA_API_KEY_ID="..."
export APCA_API_SECRET_KEY="..."
export ALPACA_DATA_FEED="iex"
export MARKET_DATA_QUOTE_MAX_AGE_SECONDS="15"
```

When `MARKET_DATA_SYMBOLS` is omitted, the Alpaca collector subscribes to the Dashboard's four default US stocks: `AAPL.US,MSFT.US,NVDA.US,TSLA.US`. Override it when a different live set is required:

```bash
export MARKET_DATA_SYMBOLS="AAPL.US,MSFT.US,NVDA.US,TSLA.US"
```

`ALPACA_DATA_FEED` accepts:

- `iex`: real-time IEX feed, commonly available on Alpaca Basic.
- `sip`: real-time consolidated SIP feed when the Alpaca subscription permits it.
- `delayed_sip`: delayed SIP data. Quotes from this feed are explicitly returned with `status="delayed"` and are never presented as live.

A single `StockDataStream` is shared by the service process. `data_timeout=60` is enabled so the SDK can reconnect a socket that remains connected but stops delivering data.

If both Alpaca credential variables are absent, the service starts with the collector disabled. This is intentional: health checks and the quote API remain available, while the static Dashboard continues to work. Partial credentials, an invalid feed, or non-US symbols are configuration errors and fail fast.

## Alpaca historical bars

The service package also provides `AlpacaHistoricalProvider` for provider-neutral US equity history. It uses the same server-side `AlpacaConfig` credentials and supports the canonical `BarTimeframe.DAY_1` (`1d`) and `BarTimeframe.MINUTE_1` (`1m`) contracts.

Historical requests:

- normalize `AAPL.US` / `us:AAPL` through the existing US instrument model;
- propagate the configured IEX/SIP/delayed SIP feed;
- request `Adjustment.ALL` so corporate-action normalization is explicit;
- execute Alpaca's synchronous `get_stock_bars()` call through `asyncio.to_thread`, keeping async service callers non-blocking;
- return provider-neutral `Bar` records with timezone-aware timestamps, validated OHLC values, volume, timeframe and source metadata;
- return an empty list for a valid request with no bars rather than inventing data.

The historical provider is exposed through the read-only `/v1/bars/{symbol}` REST endpoint when Alpaca credentials are configured. The Dashboard uses this endpoint through `MARKET_DATA_SERVICE_URL` and keeps its existing cache as a fallback. The historical endpoint is not restricted to the collector's default live subscription list; any valid US symbol can be requested.

## Run locally

From the repository root:

```bash
uv run --package market-data-service \
  uvicorn market_data_service.app:app --host 127.0.0.1 --port 8000
```

Endpoints:

```text
GET /healthz
GET /v1/quotes/AAPL.US
GET /v1/bars/TSLA.US?start=2026-08-01T00:00:00Z&end=2026-08-27T00:00:00Z&timeframe=1d
WS  /v1/stream?symbols=AAPL,MSFT,NVDA,TSLA
```

Quote payloads use the provider-neutral contract:

```json
{
  "symbol": "us:AAPL",
  "price": 201.25,
  "timestamp": "2026-08-27T14:31:00+00:00",
  "source": "alpaca",
  "status": "live",
  "freshness": "current"
}
```

`freshness` is calculated by this service. A quote older than `MARKET_DATA_QUOTE_MAX_AGE_SECONDS` becomes `stale`; the WebSocket emits that transition even if no new Alpaca trade arrives.

## Dashboard integration

The browser never connects to Alpaca directly. Build the Dashboard with an absolute service origin:

```bash
export VITE_MARKET_DATA_URL="https://market-data.example.com"
```

The SPA renders `data.json` first. For US instruments it then opens the optional service WebSocket and overlays only the current displayed price/status. Historical daily and intraday arrays are fetched server-side through the Dashboard data facade, with the static cache as fallback. If the WebSocket disconnects, the quote is marked stale and the UI falls back to the static snapshot price while reconnecting.

## Scope

This service does not expose trading, account, order, or portfolio APIs. US historical bars are read-only and require configured Alpaca credentials. Hong Kong historical/minute compatibility remains in the Dashboard data facade; Hong Kong minute data is treated as delayed compatibility data rather than a live stream.
