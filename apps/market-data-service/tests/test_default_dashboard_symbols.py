from market_data_service.config import AlpacaConfig


def test_alpaca_default_symbols_cover_dashboard_us_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.delenv("MARKET_DATA_SYMBOLS", raising=False)

    config = AlpacaConfig.from_env()

    assert config.symbols == (
        "us:AAPL",
        "us:MSFT",
        "us:NVDA",
        "us:TSLA",
    )
