from types import SimpleNamespace

import pytest

from trading_research.strategies import rbreaker


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_calculates_six_levels_from_previous_day() -> None:
    strategy = rbreaker.RBreakerStrategy.__new__(rbreaker.RBreakerStrategy)
    strategy.p = SimpleNamespace(f1=0.35, f2=0.07, f3=0.25)
    strategy.ssetup = strategy.bsetup = 0.0
    strategy.senter = strategy.benter = 0.0
    strategy.bbreak = strategy.sbreak = 0.0

    strategy.calculate_levels(110.0, 100.0, 105.0)

    assert strategy.ssetup == pytest.approx(111.75)
    assert strategy.bsetup == pytest.approx(98.25)
    assert strategy.senter == pytest.approx(108.025)
    assert strategy.benter == pytest.approx(101.975)
    assert strategy.bbreak == pytest.approx(115.125)
    assert strategy.sbreak == pytest.approx(94.875)


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_ignores_invalid_previous_day_range() -> None:
    strategy = rbreaker.RBreakerStrategy.__new__(rbreaker.RBreakerStrategy)
    strategy.p = SimpleNamespace(f1=0.35, f2=0.07, f3=0.25)
    strategy.ssetup = 111.0
    strategy.bsetup = 99.0
    strategy.senter = 108.0
    strategy.benter = 102.0
    strategy.bbreak = 115.0
    strategy.sbreak = 95.0

    strategy.calculate_levels(100.0, 100.0, 100.0)

    assert (strategy.ssetup, strategy.bsetup) == (111.0, 99.0)
