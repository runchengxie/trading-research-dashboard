from datetime import UTC, datetime

from fastapi.testclient import TestClient

from market_data_service.app import create_app
from market_data_service.contracts import Bar


class FakeHistoricalProvider:
    async def fetch_bars(self, symbol, *, start, end, timeframe):
        return [
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime(2026, 8, 26, 14, 30, tzinfo=UTC),
                open=200,
                high=202,
                low=199,
                close=201,
                volume=1000,
                source="fake",
            )
        ]


def test_historical_bars_endpoint_returns_normalized_bars() -> None:
    client = TestClient(create_app(historical_provider=FakeHistoricalProvider()))

    response = client.get(
        "/v1/bars/AAPL.US",
        params={"start": "2026-08-01T00:00:00Z", "end": "2026-08-27T00:00:00Z", "timeframe": "1d"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "us:AAPL",
        "timeframe": "1d",
        "bars": [
            {
                "symbol": "us:AAPL",
                "timeframe": "1d",
                "timestamp": "2026-08-26T14:30:00+00:00",
                "open": 200.0,
                "high": 202.0,
                "low": 199.0,
                "close": 201.0,
                "volume": 1000.0,
                "source": "fake",
            }
        ],
    }


def test_historical_bars_endpoint_requires_provider() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/bars/AAPL.US",
        params={"start": "2026-08-01T00:00:00Z", "end": "2026-08-27T00:00:00Z", "timeframe": "1d"},
    )

    assert response.status_code == 503
