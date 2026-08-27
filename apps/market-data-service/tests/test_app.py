from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from market_data_service.app import create_app, create_app_from_env
from market_data_service.contracts import Quote
from market_data_service.state import QuoteStore


def test_healthz_is_available_without_alpaca_credentials() -> None:
    client = TestClient(create_app(store=QuoteStore()))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_app_from_env_allows_missing_credentials_but_rejects_invalid_config(monkeypatch) -> None:
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    client = TestClient(create_app_from_env())
    assert client.get("/healthz").json()["collectorConfigured"] is False

    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.setenv("ALPACA_DATA_FEED", "boats")
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "AAPL.US")
    with pytest.raises(ValueError, match="ALPACA_DATA_FEED"):
        create_app_from_env()


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


def test_websocket_stream_emits_requested_quote() -> None:
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, datetime.now(UTC), "alpaca"))
    client = TestClient(create_app(store=store))

    with client.websocket_connect("/v1/stream?symbols=AAPL") as websocket:
        payload = websocket.receive_json()

    assert payload["symbol"] == "us:AAPL"
    assert payload["price"] == 201.25
    assert payload["freshness"] == "current"
