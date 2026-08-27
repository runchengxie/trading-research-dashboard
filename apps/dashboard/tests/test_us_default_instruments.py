from trading_research.dashboard import astock_tech

DEFAULT_US_CODES = ("AAPL.US", "MSFT.US", "NVDA.US", "TSLA.US")


def test_dashboard_defaults_include_four_us_stocks() -> None:
    assert list(astock_tech.STOCK_CONFIG) == ["sz300246", *DEFAULT_US_CODES]

    expected_names = {
        "AAPL.US": "Apple",
        "MSFT.US": "Microsoft",
        "NVDA.US": "NVIDIA",
        "TSLA.US": "Tesla",
    }
    for code, name in expected_names.items():
        config = astock_tech.STOCK_CONFIG[code]
        assert config["name"] == name
        assert config["instrument_type"] == "stock"
        assert config["market"] == "US"


def test_code_selection_synthesizes_unlisted_decorated_us_stock() -> None:
    configs = astock_tech._resolve_config_items(["AMD.US", "us:GOOGL"])

    assert list(configs) == ["AMD.US", "us:GOOGL"]
    assert configs["AMD.US"] == {
        "name": "AMD",
        "instrument_type": "stock",
        "market": "US",
    }
    assert configs["us:GOOGL"] == {
        "name": "GOOGL",
        "instrument_type": "stock",
        "market": "US",
    }
