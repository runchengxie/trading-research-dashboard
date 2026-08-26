import importlib


def test_dashboard_python_modules_are_importable_from_trading_research() -> None:
    dashboard = importlib.import_module("trading_research.dashboard.astock_tech")
    data_sources = importlib.import_module("trading_research.data.data_sources")
    rbreaker = importlib.import_module("trading_research.strategies.rbreaker")

    assert callable(dashboard.main)
    assert callable(data_sources.fetch_daily)
    assert hasattr(rbreaker, "main")


def test_source_root_compatibility_modules_are_not_required() -> None:
    assert importlib.util.find_spec("astock_tech") is None
    assert importlib.util.find_spec("data_sources") is None
