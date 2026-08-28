from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect

from .collector import AlpacaCollector
from .config import AlpacaConfig, ServiceConfig
from .contracts import Bar, BarTimeframe
from .provider import HistoricalMarketDataProvider
from .providers.alpaca import AlpacaStockProvider
from .providers.alpaca_historical import AlpacaHistoricalProvider
from .providers.yfinance_historical import YFinanceHistoricalProvider
from .redis_state import RedisQuoteStore, SyncRedisQuoteStore
from .state import QuoteState, QuoteStore
from .symbols import Market, parse_instrument


def _quote_payload(state: QuoteState) -> dict[str, object]:
    quote = state.quote
    return {
        "symbol": quote.symbol,
        "price": quote.price,
        "timestamp": quote.timestamp.isoformat(),
        "source": quote.source,
        "status": quote.status.value,
        "freshness": state.freshness.value,
    }


def _bar_payload(bar: Bar) -> dict[str, object]:
    return {
        "symbol": bar.symbol,
        "timeframe": bar.timeframe.value,
        "timestamp": bar.timestamp.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "source": bar.source,
    }


async def _get_quote(store: object, symbol: str, *, now: datetime) -> QuoteState | None:
    getter = getattr(store, "get_quote", None)
    if getter is None:
        getter = cast(Any, store).get
    result = getter(symbol, now=now)
    if inspect.isawaitable(result):
        return await result
    return result


def create_app(
    *,
    store: object | None = None,
    collector: AlpacaCollector | None = None,
    historical_provider: HistoricalMarketDataProvider | None = None,
    redis_client: object | None = None,
) -> FastAPI:
    quote_store = store or QuoteStore()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if collector is not None:
            collector.start()
        try:
            yield
        finally:
            if collector is not None:
                collector.stop()
            if redis_client is not None:
                close = getattr(redis_client, "aclose", None)
                if close is not None:
                    result = close()
                    if inspect.isawaitable(result):
                        await result

    app = FastAPI(title="Market Data Service", lifespan=lifespan)
    app.state.quote_store = quote_store
    app.state.collector_configured = collector is not None
    app.state.historical_provider_configured = historical_provider is not None
    app.state.redis_client = redis_client

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return {
            "status": "ok",
            "collectorConfigured": app.state.collector_configured,
        }

    @app.get("/readyz")
    async def readyz(response: Response) -> dict[str, object]:
        redis_status = "disabled"
        if redis_client is not None:
            try:
                ping = cast(Any, redis_client).ping
                result = ping()
                if inspect.isawaitable(result):
                    await result
                redis_status = "ok"
            except Exception:
                redis_status = "unavailable"
        collector_status = "disabled"
        if collector is not None:
            collector_status = "configured"
            if isinstance(quote_store, RedisQuoteStore):
                heartbeat = await quote_store.get_heartbeat()
                collector_status = "healthy" if heartbeat is not None else "stale"
        ready = redis_status in {"ok", "disabled"} and collector_status in {
            "configured",
            "healthy",
            "disabled",
        }
        if not ready:
            response.status_code = 503
        return {
            "status": "ready" if ready else "not_ready",
            "redis": redis_status,
            "collector": collector_status,
        }

    @app.get("/v1/quotes/{symbol}")
    async def get_quote(symbol: str) -> dict[str, object]:
        try:
            state = await _get_quote(quote_store, symbol, now=datetime.now(UTC))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if state is None:
            raise HTTPException(status_code=404, detail="quote not available")
        return _quote_payload(state)

    @app.get("/v1/bars/{symbol}")
    async def get_bars(
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: BarTimeframe = BarTimeframe.DAY_1,
    ) -> dict[str, object]:
        if historical_provider is None:
            raise HTTPException(status_code=503, detail="historical provider not configured")
        try:
            bars = await historical_provider.fetch_bars(
                symbol,
                start=start,
                end=end,
                timeframe=timeframe,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "symbol": bars[0].symbol if bars else symbol,
            "timeframe": timeframe.value,
            "bars": [_bar_payload(bar) for bar in bars],
        }

    @app.websocket("/v1/stream")
    async def stream_quotes(websocket: WebSocket, symbols: str = "") -> None:
        requested = []
        try:
            for raw in symbols.split(","):
                value = raw.strip()
                if not value:
                    continue
                requested.append(parse_instrument(value, market=Market.US).symbol)
        except ValueError:
            await websocket.close(code=1008)
            return

        if not requested:
            await websocket.close(code=1008)
            return

        requested = list(dict.fromkeys(requested))
        await websocket.accept()
        if isinstance(quote_store, RedisQuoteStore):
            try:
                async with quote_store.subscribe_quotes(requested) as subscription:
                    for symbol in requested:
                        state = await quote_store.get_quote(symbol, now=datetime.now(UTC))
                        if state is not None:
                            await websocket.send_json(_quote_payload(state))
                    async for quote in subscription:
                        state = await quote_store.get_quote(quote.symbol, now=datetime.now(UTC))
                        if state is not None:
                            await websocket.send_json(_quote_payload(state))
            except WebSocketDisconnect:
                return
            return
        last_sent: dict[str, tuple[str, str]] = {}
        try:
            while True:
                now = datetime.now(UTC)
                for symbol in requested:
                    state = await _get_quote(quote_store, symbol, now=now)
                    if state is None:
                        continue
                    marker = (state.quote.timestamp.isoformat(), state.freshness.value)
                    if last_sent.get(symbol) == marker:
                        continue
                    await websocket.send_json(_quote_payload(state))
                    last_sent[symbol] = marker
                await asyncio.sleep(0.25)
        except WebSocketDisconnect:
            return

    return app


def create_app_from_env() -> FastAPI:
    service_config = ServiceConfig.from_env()
    store: object = QuoteStore(max_age_seconds=service_config.quote_max_age_seconds)
    collector_store: object = store
    redis_client = None
    if redis_url := os.getenv("REDIS_URL", "").strip():
        import redis
        from redis import asyncio as redis_asyncio

        sync_redis = redis.Redis.from_url(redis_url, decode_responses=True)
        redis_client = redis_asyncio.Redis.from_url(redis_url, decode_responses=True)
        store = RedisQuoteStore(
            cast(Any, redis_client),
            max_age_seconds=service_config.quote_max_age_seconds,
        )
        collector_store = SyncRedisQuoteStore(sync_redis)

    api_key = os.getenv("APCA_API_KEY_ID", "").strip()
    secret_key = os.getenv("APCA_API_SECRET_KEY", "").strip()
    collector: AlpacaCollector | None = None
    historical_provider: HistoricalMarketDataProvider | None = None
    historical_source = os.getenv("MARKET_DATA_HISTORICAL_PROVIDER", "auto").strip().lower()
    if historical_source not in {"auto", "alpaca", "yfinance", "none"}:
        raise ValueError(
            "MARKET_DATA_HISTORICAL_PROVIDER must be one of: auto, alpaca, yfinance, none"
        )
    if api_key or secret_key:
        alpaca_config = AlpacaConfig.from_env()
        collector = AlpacaCollector(
            AlpacaStockProvider(alpaca_config),
            collector_store,
            heartbeat_sink=(
                cast(Any, collector_store) if redis_client is not None else None
            ),
        )
    if historical_source == "alpaca":
        if not api_key or not secret_key:
            raise ValueError("Alpaca historical provider requires both API credentials")
        historical_provider = AlpacaHistoricalProvider(alpaca_config)
    elif historical_source == "yfinance":
        historical_provider = YFinanceHistoricalProvider()
    elif historical_source == "auto":
        if api_key and secret_key:
            historical_provider = AlpacaHistoricalProvider(alpaca_config)
        else:
            historical_provider = YFinanceHistoricalProvider()

    return create_app(
        store=store,
        collector=collector,
        historical_provider=historical_provider,
        redis_client=redis_client,
    )


app = create_app_from_env()
