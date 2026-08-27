from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .collector import AlpacaCollector
from .config import AlpacaConfig, ServiceConfig
from .providers.alpaca import AlpacaStockProvider
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


def create_app(
    *,
    store: QuoteStore | None = None,
    collector: AlpacaCollector | None = None,
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

    app = FastAPI(title="Market Data Service", lifespan=lifespan)
    app.state.quote_store = quote_store
    app.state.collector_configured = collector is not None

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return {
            "status": "ok",
            "collectorConfigured": app.state.collector_configured,
        }

    @app.get("/v1/quotes/{symbol}")
    async def get_quote(symbol: str) -> dict[str, object]:
        try:
            state = quote_store.get(symbol, now=datetime.now(UTC))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if state is None:
            raise HTTPException(status_code=404, detail="quote not available")
        return _quote_payload(state)

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
        last_sent: dict[str, tuple[str, str]] = {}
        try:
            while True:
                now = datetime.now(UTC)
                for symbol in requested:
                    state = quote_store.get(symbol, now=now)
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
    store = QuoteStore(max_age_seconds=service_config.quote_max_age_seconds)

    api_key = os.getenv("APCA_API_KEY_ID", "").strip()
    secret_key = os.getenv("APCA_API_SECRET_KEY", "").strip()
    collector: AlpacaCollector | None = None
    if api_key or secret_key:
        alpaca_config = AlpacaConfig.from_env()
        collector = AlpacaCollector(AlpacaStockProvider(alpaca_config), store)

    return create_app(store=store, collector=collector)


app = create_app_from_env()
