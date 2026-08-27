import pytest

from trading_research.dashboard import astock_tech


def test_default_dashboard_instrument_is_baolaite() -> None:
    assert list(astock_tech.STOCK_CONFIG) == [
        "sz300246",
        "AAPL.US",
        "MSFT.US",
        "NVDA.US",
        "TSLA.US",
    ]
    assert astock_tech.STOCK_CONFIG["sz300246"]["name"] == "宝莱特"
    assert astock_tech.STOCK_CONFIG["sz300246"]["instrument_type"] == "stock"


def test_default_us_instruments_use_us_market_profile() -> None:
    for code in ("AAPL.US", "MSFT.US", "NVDA.US", "TSLA.US"):
        config = astock_tech.STOCK_CONFIG[code]
        assert config["market"] == "US"
        assert config["instrument_type"] == "stock"
        assert config["currency"] == "USD"
        assert config["timezone"] == "America/New_York"


def test_explicit_us_codes_are_resolved_even_when_not_preconfigured() -> None:
    resolved = astock_tech.resolve_stock_config(["AMD.US", "us:GOOGL"])

    assert list(resolved) == ["AMD.US", "us:GOOGL"]
    assert resolved["AMD.US"] == {
        "name": "AMD",
        "market": "US",
        "instrument_type": "stock",
        "currency": "USD",
        "timezone": "America/New_York",
    }
    assert resolved["us:GOOGL"]["name"] == "GOOGL"


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
