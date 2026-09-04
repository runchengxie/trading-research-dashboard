import pytest

from trading_research.dashboard.instrument_config import (
    resolve_stock_config,
    vwap_deviation_override,
)


def test_resolve_stock_config_adds_unknown_explicit_us_ticker() -> None:
    result = resolve_stock_config(["AMD.US"])

    assert result["AMD.US"] == {
        "name": "AMD",
        "market": "US",
        "instrument_type": "stock",
        "currency": "USD",
        "timezone": "America/New_York",
    }


def test_vwap_deviation_override_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        vwap_deviation_override({"vwap_dev_k": 0})
