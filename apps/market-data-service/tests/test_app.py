from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from market_data_service.app import create_app, create_app_from_env
from market_data_service.contracts import Quote
from market_data_service.redis_state import RedisQuoteStore
from market_data_service.state import QuoteStore


class _RedisRuntime:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error

    async def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return True

    async def get(self, name: str):
        del name
        return None

    async def aclose(self) -> None:
        return None


def test_readiness_recovers_when_redis_becomes_available() -> None:
    redis = _RedisRuntime(ping_error=ConnectionError("redis down"))
    client = TestClient(
        create_app(store=RedisQuoteStore(redis), redis_client=redis)
    )

    unavailable = client.get("/readyz")
    redis.ping_error = None
    available = client.get("/readyz")

    assert unavailable.status_code == 503
    assert available.status_code == 200
    assert available.json()["redis"] == "ok"


def test_healthz_is_available_without_alpaca_credentials() -> None:
    client = TestClient(create_app(store=QuoteStore()))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_app_from_env_allows_missing_credentials_but_rejects_invalid_config(monkeypatch) -> None:
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    app = create_app_from_env()
    client = TestClient(app)
    assert client.get("/healthz").json()["collectorConfigured"] is False
    assert app.state.historical_provider_configured is True

    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.setenv("ALPACA_DATA_FEED", "boats")
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "AAPL.US")
    with pytest.raises(ValueError, match="ALPACA_DATA_FEED"):
        create_app_from_env()


def test_create_app_from_env_can_disable_historical_provider(monkeypatch) -> None:
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    monkeypatch.setenv("MARKET_DATA_HISTORICAL_PROVIDER", "none")

    client = TestClient(create_app_from_env())

    response = client.get(
        "/v1/bars/AAPL.US",
        params={
            "start": "2026-08-01T00:00:00Z",
            "end": "2026-08-02T00:00:00Z",
            "timeframe": "1d",
        },
    )
    assert response.status_code == 503


def test_create_app_from_env_can_select_yfinance_with_alpaca_credentials(monkeypatch) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "AAPL.US")
    monkeypatch.setenv("MARKET_DATA_HISTORICAL_PROVIDER", "yfinance")

    app = create_app_from_env()

    assert app.state.historical_provider_configured is True
    assert app.state.collector_configured is True


def test_quote_endpoint_returns_normalized_quote_and_freshness() -> None:
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, datetime.now(UTC), "alpaca"))
    client = TestClient(create_app(store=store))

    response = client.get("/v1/quotes/AAPL.US")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "us:AAPL"
    assert payload["price"] == 201.25
    assert payload["source"] == "alpaca"
    assert payload["freshness"] == "current"


def test_quote_endpoint_returns_404_when_quote_is_missing() -> None:
    client = TestClient(create_app(store=QuoteStore()))

    response = client.get("/v1/quotes/MSFT.US")

    assert response.status_code == 404


def test_redis_runtime_is_used_by_readiness_and_quote_api() -> None:
    redis = _RedisRuntime()
    client = TestClient(
        create_app(
            store=RedisQuoteStore(redis),
            redis_client=redis,
        )
    )

    readiness = client.get("/readyz")
    quote = client.get("/v1/quotes/AAPL.US")

    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "ready",
        "redis": "ok",
        "collector": "disabled",
    }
    assert quote.status_code == 404


def test_readiness_returns_503_when_redis_is_unavailable() -> None:
    redis = _RedisRuntime(ping_error=ConnectionError("redis down"))
    client = TestClient(
        create_app(
            store=RedisQuoteStore(redis),
            redis_client=redis,
        )
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["redis"] == "unavailable"


def test_websocket_stream_emits_requested_quote() -> None:
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, datetime.now(UTC), "alpaca"))
    client = TestClient(create_app(store=store))

    with client.websocket_connect("/v1/stream?symbols=AAPL") as websocket:
        payload = websocket.receive_json()

    assert payload["symbol"] == "us:AAPL"
    assert payload["price"] == 201.25
    assert payload["freshness"] == "current"


def test_websocket_client_can_reconnect_and_receive_current_quote() -> None:
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, datetime.now(UTC), "alpaca"))
    client = TestClient(create_app(store=store))

    for expected_price in (201.25, 202.0):
        if expected_price == 202.0:
            store.put(Quote("AAPL.US", expected_price, datetime.now(UTC), "alpaca"))
        with client.websocket_connect("/v1/stream?symbols=AAPL") as websocket:
            assert websocket.receive_json()["price"] == expected_price
