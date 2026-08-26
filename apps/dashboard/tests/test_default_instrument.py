from trading_research.dashboard.astock_tech import STOCK_CONFIG


def test_default_dashboard_instrument_is_baolaite() -> None:
    assert list(STOCK_CONFIG) == ["sz300246"]
    assert STOCK_CONFIG["sz300246"]["name"] == "宝莱特"
    assert STOCK_CONFIG["sz300246"]["instrument_type"] == "stock"
