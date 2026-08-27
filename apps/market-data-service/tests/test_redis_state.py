import importlib.util


def test_redis_state_module_is_available() -> None:
    assert importlib.util.find_spec("market_data_service.redis_state") is not None
