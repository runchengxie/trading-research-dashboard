from __future__ import annotations

import pandas as pd

from trading_research.scripts.prepare_agent_prices import build_price_payload


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
