import pytest

from trading_research.dashboard import astock_tech


def test_default_dashboard_instruments_include_baolaite_and_us_stocks() -> None:
    assert list(astock_tech.STOCK_CONFIG) == [
        "sz300246",
        "AAPL.US",
        "MSFT.US",
        "NVDA.US",
        "TSLA.US",
    ]
    assert astock_tech.STOCK_CONFIG["sz300246"]["name"] == "宝莱特"
    assert astock_tech.STOCK_CONFIG["sz300246"]["instrument_type"] == "stock"


@pytest.mark.parametrize(
    ("style", "expected"),
    (
        ("Mean reversion + VWAP", 0.4),
        ("Trend-following + Breakout", 0.6),
        ("Breakout + Momentum", 0.5),
        ("Trend-following + Grid", 0.5),
        ("Mean reversion + Range", 0.5),
    ),
)
def test_trading_style_maps_to_expected_vwap_factor(
    style: str, expected: float
) -> None:
    assert astock_tech.vwap_deviation_factor_for_style(style) == expected
