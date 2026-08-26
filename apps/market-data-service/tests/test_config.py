from market_data_service.config import ServiceConfig


def test_service_config_has_safe_static_fallback_defaults(monkeypatch) -> None:
    monkeypatch.delenv("MARKET_DATA_QUOTE_MAX_AGE_SECONDS", raising=False)
    monkeypatch.delenv("MARKET_DATA_SYMBOLS", raising=False)

    config = ServiceConfig.from_env()

    assert config.quote_max_age_seconds == 15
    assert config.symbols == ("sz300246",)
