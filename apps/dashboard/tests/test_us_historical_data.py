from __future__ import annotations

from trading_research.data import market_compat as ds


def test_fetch_daily_us_maps_service_bars_to_dashboard_schema(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_DATA_SERVICE_URL", "http://market-data.test")
    monkeypatch.setattr(
        ds,
        "_fetch_us_bars",
        lambda **kwargs: [
            {
                "timestamp": "2026-08-26T14:30:00+00:00",
                "open": 200,
                "high": 202,
                "low": 199,
                "close": 201,
                "volume": 1000,
            }
        ],
    )

    result = ds.fetch_daily("AAPL.US", "20260801", "20260826", market="US")

    assert list(result.columns) == ["date", "open", "close", "high", "low", "volume"]
    assert result.to_dict("records") == [
        {"date": "2026-08-26", "open": 200, "close": 201, "high": 202, "low": 199, "volume": 1000}
    ]


def test_fetch_intraday_us_maps_close_to_existing_intraday_schema(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_DATA_SERVICE_URL", "http://market-data.test")
    monkeypatch.setattr(
        ds,
        "_fetch_us_bars",
        lambda **kwargs: [
            {
                "timestamp": "2026-08-26T14:31:00+00:00",
                "open": 200,
                "high": 202,
                "low": 199,
                "close": 201,
                "volume": 1000,
            }
        ],
    )

    result = ds.fetch_intraday("us:AAPL", "2026-08-26", market="US")

    assert list(result.columns) == ["time", "price", "volume"]
    assert result.to_dict("records") == [{"time": "10:31:00", "price": 201, "volume": 1000}]


def test_fetch_daily_us_falls_back_to_direct_yfinance_when_service_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(ds, "_fetch_us_bars", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(
        ds,
        "_fetch_us_bars_yfinance",
        lambda **kwargs: [
            {
                "timestamp": "2026-08-26T14:30:00+00:00",
                "open": 200,
                "high": 202,
                "low": 199,
                "close": 201,
                "volume": 1000,
            }
        ],
    )

    result = ds.fetch_daily("AAPL.US", "20260801", "20260826", market="US")

    assert result["close"].tolist() == [201]


def test_fetch_intraday_us_falls_back_to_direct_yfinance_when_service_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(ds, "_fetch_us_bars", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(
        ds,
        "_fetch_us_bars_yfinance",
        lambda **kwargs: [
            {
                "timestamp": "2026-08-26T14:31:00+00:00",
                "open": 200,
                "high": 202,
                "low": 199,
                "close": 201,
                "volume": 1000,
            }
        ],
    )

    result = ds.fetch_intraday("us:AAPL", "2026-08-26", market="US")

    assert result.to_dict("records") == [{"time": "10:31:00", "price": 201, "volume": 1000}]
