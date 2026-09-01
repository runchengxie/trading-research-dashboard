from __future__ import annotations

import pandas as pd

from trading_research.scripts.prepare_agent_prices import (
    DEFAULT_STOCK_SYMBOLS,
    DEFAULT_SYMBOLS,
    build_price_payload,
    symbols_for_universe,
)


def test_default_symbols_are_tradable_a_share_etfs() -> None:
    assert DEFAULT_SYMBOLS == ("510300.SH", "512100.SH", "159915.SZ", "511010.SH")


def test_stock_universe_exposes_a_small_explicit_paper_trading_basket() -> None:
    assert DEFAULT_STOCK_SYMBOLS == (
        "600519.SH",
        "000858.SZ",
        "601318.SH",
        "600036.SH",
        "300750.SZ",
    )
    assert symbols_for_universe("etf") == DEFAULT_SYMBOLS
    assert symbols_for_universe("stocks") == DEFAULT_STOCK_SYMBOLS


def test_symbols_for_universe_rejects_unknown_universe() -> None:
    try:
        symbols_for_universe("crypto")
    except ValueError as error:
        assert str(error) == "universe must be etf or stocks"
    else:
        raise AssertionError("expected an unknown universe to fail")


def test_build_price_payload_uses_latest_valid_close() -> None:
    payload = build_price_payload(
        {
            "SPY": pd.DataFrame({"Close": [100.0, 101.5]}, index=pd.to_datetime(["2026-08-31", "2026-09-01"])),
            "QQQ": pd.DataFrame({"Close": [200.0]}, index=pd.to_datetime(["2026-09-01"])),
        }
    )
    assert payload == {"asOf": "2026-09-01", "prices": {"SPY": 101.5, "QQQ": 200.0}}


def test_build_price_payload_rejects_missing_close_data() -> None:
    try:
        build_price_payload({"SPY": pd.DataFrame()})
    except ValueError as error:
        assert "no valid close" in str(error)
    else:
        raise AssertionError("expected missing close data to fail")


def test_build_price_payload_accepts_tushare_daily_columns() -> None:
    payload = build_price_payload(
        {
            "510300.SH": pd.DataFrame(
                {"trade_date": ["20260901", "20260902"], "close": [4.1, 4.2]}
            )
        }
    )
    assert payload == {
        "asOf": "2026-09-02",
        "prices": {"510300.SH": 4.2},
        "previousCloses": {"510300.SH": 4.1},
    }


def test_fetch_prices_uses_existing_tushare_client_factory(monkeypatch) -> None:
    class FakeClient:
        def fund_daily(self, *, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
            assert ts_code == "510300.SH"
            return pd.DataFrame(
                {"trade_date": ["20260901"], "close": [4.2]}
            )

    import trading_research.data.data_sources as data_sources
    from trading_research.scripts import prepare_agent_prices

    monkeypatch.setenv("TUSHARE_TOKEN_2", "token")
    monkeypatch.setattr(data_sources, "get_tushare_client", lambda token_env: FakeClient())
    payload = prepare_agent_prices.fetch_prices(("510300.SH",))

    assert payload["prices"] == {"510300.SH": 4.2}
