from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from trading_research.strategies import rbreaker
from trading_research.strategies.rbreaker_math import calculate_levels


def test_calculate_levels_is_independent_of_backtrader() -> None:
    levels = calculate_levels(110.0, 100.0, 105.0, f1=0.35, f2=0.07, f3=0.25)

    assert levels == pytest.approx((111.75, 98.25, 108.025, 101.975, 115.125, 94.875))


def test_session_close_gate_starts_at_configured_minute() -> None:
    assert rbreaker.is_session_close_or_later(datetime(2026, 7, 14, 14, 54).time(), 14, 55) is False
    assert rbreaker.is_session_close_or_later(datetime(2026, 7, 14, 14, 55).time(), 14, 55) is True
    assert rbreaker.is_session_close_or_later(datetime(2026, 7, 14, 15, 0).time(), 14, 55) is True


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


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_records_long_breakout_signal() -> None:
    strategy = SimpleNamespace(
        data=SimpleNamespace(close=[116.0], datetime=SimpleNamespace(datetime=lambda _: datetime(2026, 1, 1))),
        position=None,
        bbreak=115.0,
        sbreak=95.0,
        order=None,
        stop_order=None,
        p=SimpleNamespace(reverse=2.0),
        bought=False,
        trade_signals=[],
    )
    strategy.buy = lambda: setattr(strategy, "bought", True) or "buy-order"
    strategy.record_signal = lambda kind, price, when: strategy.trade_signals.append(kind)

    rbreaker.RBreakerStrategy.check_signals(strategy)

    assert strategy.bought is True
    assert strategy.order == "buy-order"
    assert strategy.trade_signals == ["Long"]


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_reverses_long_position_and_sets_stop() -> None:
    calls: list[tuple[str, dict]] = []
    strategy = SimpleNamespace(
        data=SimpleNamespace(close=[104.0], datetime=SimpleNamespace(datetime=lambda _: datetime(2026, 1, 1))),
        position=SimpleNamespace(size=1, price=100.0),
        bbreak=115.0,
        sbreak=95.0,
        ssetup=105.0,
        senter=106.0,
        today_high=110.0,
        today_low=100.0,
        order=None,
        stop_order=None,
        p=SimpleNamespace(reverse=2.0),
        trade_signals=[],
    )
    strategy.close = lambda **kwargs: calls.append(("close", kwargs)) or "close-order"
    strategy.sell = lambda **kwargs: calls.append(("sell", kwargs)) or "sell-order"
    strategy.record_signal = lambda kind, price, when: strategy.trade_signals.append(kind)

    rbreaker.RBreakerStrategy.check_signals(strategy)

    assert strategy.order == "sell-order"
    assert strategy.trade_signals == ["Reverse to Short"]
    assert calls == [("close", {}), ("sell", {}) , ("sell", {"exectype": rbreaker.bt.Order.Stop, "price": 98.0})]


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_close_positions_cancels_protective_stop() -> None:
    canceled: list[object] = []
    strategy = SimpleNamespace(
        position=SimpleNamespace(size=-1),
        stop_order="stop-order",
        order=None,
    )
    strategy.log = lambda *args, **kwargs: None
    strategy.close = lambda: "close-order"
    strategy.cancel = lambda order: canceled.append(order)

    rbreaker.RBreakerStrategy.close_positions(strategy)

    assert strategy.order == "close-order"
    assert canceled == ["stop-order"]


@pytest.mark.skipif(rbreaker.RBreakerStrategy is None, reason="backtrader is not installed")
def test_rbreaker_evaluates_signals_after_configured_period() -> None:
    start = datetime(2026, 1, 1, 9, 30)
    strategy = SimpleNamespace(
        data=SimpleNamespace(
            close=[102.0],
            datetime=SimpleNamespace(datetime=lambda _: start + timedelta(minutes=10)),
        ),
        p=SimpleNamespace(eval_period=10),
        trade_signals=[{"type": "Long", "price": 100.0, "time": start, "evaluated": False}],
    )

    rbreaker.RBreakerStrategy.evaluate_signals(strategy)

    assert strategy.trade_signals[0]["evaluated"] is True
    assert strategy.trade_signals[0]["outcome"] == "Correct"
