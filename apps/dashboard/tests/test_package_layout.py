import importlib


def test_dashboard_python_modules_are_importable_from_trading_research() -> None:
    dashboard = importlib.import_module("trading_research.dashboard.astock_tech")
    data_sources = importlib.import_module("trading_research.data.data_sources")
    rbreaker = importlib.import_module("trading_research.strategies.rbreaker")

    assert callable(dashboard.main)
    assert callable(data_sources.fetch_daily)
    assert hasattr(rbreaker, "main")


def test_legacy_imports_resolve_to_the_package_modules() -> None:
    assert importlib.import_module("astock_tech") is importlib.import_module(
        "trading_research.dashboard.astock_tech"
    )
    assert importlib.import_module("data_sources") is importlib.import_module(
        "trading_research.data.data_sources"
    )
    assert importlib.import_module("backtest.rbreaker") is importlib.import_module(
        "trading_research.strategies.rbreaker"
    )
