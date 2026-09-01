from __future__ import annotations

import pandas as pd

from trading_research.scripts.prepare_agent_prices import DEFAULT_SYMBOLS, build_price_payload


def test_default_symbols_are_tradable_a_share_etfs() -> None:
    assert DEFAULT_SYMBOLS == ("510300.SH", "512100.SH", "159915.SZ", "511010.SH")


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
