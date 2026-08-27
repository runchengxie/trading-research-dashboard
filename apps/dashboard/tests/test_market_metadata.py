import pandas as pd
import pytest

from trading_research.dashboard import astock_tech
from trading_research.data import market_compat


def test_market_compat_infers_decorated_market_symbols() -> None:
    assert market_compat.infer_market("sz300246") == "CN"
    assert market_compat.infer_market("00700.HK") == "HK"
    assert market_compat.infer_market("hk00700") == "HK"
    assert market_compat.infer_market("AAPL.US") == "US"
    assert market_compat.infer_market("us:AAPL") == "US"
    assert market_compat.infer_market("AAPL") == "CN"


def test_market_compat_rejects_explicit_market_that_conflicts_with_code() -> None:
    with pytest.raises(ValueError, match="冲突"):
        market_compat.infer_market("sz300246", "HK")


def test_select_intraday_trade_day_uses_market_specific_daily_dates_for_hk() -> None:
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-08-24", "2026-08-26", "2026-08-27"]),
            "close": [600.0, 610.0, 612.0],
        }
    )
    cn_calendar = pd.DataFrame({"trade_date": pd.to_datetime(["2026-08-25", "2026-08-27"])})

    selected = astock_tech.select_intraday_trade_day(
        "HK",
        daily,
        cn_calendar,
        now=pd.Timestamp("2026-08-27 12:00:00"),
    )

    assert selected == "2026-08-26"


def test_build_stock_payload_includes_optional_market_metadata() -> None:
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-08-26"]),
            "open": [600.0],
            "high": [612.0],
            "low": [598.0],
            "close": [610.0],
            "volume": [1000],
        }
    )

    payload = astock_tech.build_stock_payload(
        code="00700.HK",
        name="腾讯控股",
        instrument_type="stock",
        trading_style="Research",
        support=598.0,
        resistance=612.0,
        centers=[598.0, 602.0, 606.0, 610.0, 612.0],
        nearest_key_level=610.0,
        atr_20d=8.0,
        vwap=None,
        vwap_dev=None,
        vwap_dev_threshold=4.0,
        orb_high=None,
        orb_low=None,
        yesterday_close=610.0,
        yesterday_high=612.0,
        yesterday_low=598.0,
        daily_df=daily,
        intraday_df=pd.DataFrame(),
        intraday_day_str="2026-08-26",
        usage_notes=[],
        market="HK",
        currency="HKD",
        timezone="Asia/Hong_Kong",
    )

    assert payload["market"] == "HK"
    assert payload["currency"] == "HKD"
    assert payload["timezone"] == "Asia/Hong_Kong"
