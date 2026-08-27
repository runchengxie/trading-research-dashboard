import pytest

from market_data_service.config import AlpacaConfig, ServiceConfig


def test_service_config_has_safe_static_fallback_defaults(monkeypatch) -> None:
    monkeypatch.delenv("MARKET_DATA_QUOTE_MAX_AGE_SECONDS", raising=False)
    monkeypatch.delenv("MARKET_DATA_SYMBOLS", raising=False)

    config = ServiceConfig.from_env()

    assert config.quote_max_age_seconds == 15
    assert config.symbols == ("sz300246",)


def test_alpaca_config_reads_credentials_feed_and_us_symbols(monkeypatch) -> None:
    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.setenv("ALPACA_DATA_FEED", "sip")
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "AAPL.US,us:MSFT")

    config = AlpacaConfig.from_env()

    assert config.api_key == "key-id"
    assert config.secret_key == "secret"
    assert config.feed == "sip"
    assert config.symbols == ("us:AAPL", "us:MSFT")


def test_alpaca_config_rejects_missing_credentials_and_non_us_symbols(monkeypatch) -> None:
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "AAPL.US")
    with pytest.raises(ValueError, match="credentials"):
        AlpacaConfig.from_env()

    monkeypatch.setenv("APCA_API_KEY_ID", "key-id")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")
    monkeypatch.setenv("MARKET_DATA_SYMBOLS", "sz300246")
    with pytest.raises(ValueError, match="US symbols"):
        AlpacaConfig.from_env()
