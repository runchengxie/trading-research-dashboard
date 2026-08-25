from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    max_position_weight: float = 0.15
    risk_fraction: float = 0.01
    stop_atr_multiple: float = 2.0
    commission_bps: float = 0.0
    slippage_bps: float = 0.0
    lot_size: float = 1.0
    annualization: int = 252


@dataclass(frozen=True)
class Trade:
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    units: float
    pnl: float
    return_pct: float
    holding_bars: int
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: tuple[Trade, ...]
    metrics: dict[str, float]


def _validate_config(config: BacktestConfig) -> None:
    if config.initial_cash <= 0:
        raise ValueError("initial_cash must be positive")
    if not 0 < config.max_position_weight <= 1:
        raise ValueError("max_position_weight must be in (0, 1]")
    if not 0 < config.risk_fraction <= 1:
        raise ValueError("risk_fraction must be in (0, 1]")
    if config.stop_atr_multiple <= 0:
        raise ValueError("stop_atr_multiple must be positive")
    if config.commission_bps < 0 or config.slippage_bps < 0:
        raise ValueError("cost assumptions cannot be negative")
    if config.lot_size <= 0:
        raise ValueError("lot_size must be positive")


def _metrics(
    equity: pd.Series,
    trades: tuple[Trade, ...],
    *,
    initial_cash: float,
    annualization: int,
) -> dict[str, float]:
    if equity.empty:
        return {}

    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
    returns = equity.pct_change().dropna()
    periods = max(len(returns), 1)
    annualized_return = float((1.0 + total_return) ** (annualization / periods) - 1.0)

    volatility = float(returns.std(ddof=1)) if len(returns) > 1 else float("nan")
    sharpe = (
        float(returns.mean() / volatility * sqrt(annualization))
        if volatility and np.isfinite(volatility) and volatility > 0
        else float("nan")
    )

    running_peak = equity.cummax()
    drawdown = equity / running_peak - 1.0
    max_drawdown = float(drawdown.min())

    pnls = [trade.pnl for trade in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    if losses:
        profit_factor = float(sum(wins) / abs(sum(losses)))
    elif wins:
        profit_factor = float("inf")
    else:
        profit_factor = float("nan")

    return {
        "final_equity": float(equity.iloc[-1]),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "trade_count": float(len(trades)),
        "win_rate": float(len(wins) / len(trades)) if trades else float("nan"),
        "profit_factor": profit_factor,
    }


def run_backtest(
    signals: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run a single-asset, close-signal/next-open event-driven backtest.

    Entry and moving-average exit signals observed on bar ``t`` execute at bar
    ``t+1`` open. The protective stop is established at entry and is active
    intrabar from that point onward. A gap through the stop fills at the open,
    preventing the usual optimistic stop-price assumption.
    """

    config = config or BacktestConfig()
    _validate_config(config)
    required = {
        "open",
        "high",
        "low",
        "close",
        "atr",
        "entry_signal",
        "exit_signal",
    }
    missing = sorted(required.difference(signals.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    if signals.empty:
        raise ValueError("signals cannot be empty")

    commission_rate = config.commission_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0

    cash = float(config.initial_cash)
    units = 0.0
    entry_price = 0.0
    entry_time: Any = None
    entry_index = -1
    entry_commission = 0.0
    stop_price = float("nan")

    pending_entry_atr: float | None = None
    pending_exit = False
    trades: list[Trade] = []
    curve_records: list[dict[str, float]] = []

    def close_position(
        *,
        time: Any,
        bar_index: int,
        fill_price: float,
        reason: str,
    ) -> None:
        nonlocal cash, units, entry_price, entry_time, entry_index
        nonlocal entry_commission, stop_price

        exit_notional = units * fill_price
        exit_commission = exit_notional * commission_rate
        cash += exit_notional - exit_commission
        pnl = (fill_price - entry_price) * units - entry_commission - exit_commission
        invested = entry_price * units + entry_commission
        trades.append(
            Trade(
                entry_time=entry_time,
                exit_time=time,
                entry_price=float(entry_price),
                exit_price=float(fill_price),
                units=float(units),
                pnl=float(pnl),
                return_pct=float(pnl / invested) if invested else float("nan"),
                holding_bars=max(bar_index - entry_index, 0),
                exit_reason=reason,
            )
        )
        units = 0.0
        entry_price = 0.0
        entry_time = None
        entry_index = -1
        entry_commission = 0.0
        stop_price = float("nan")

    for bar_index, (time, row) in enumerate(signals.iterrows()):
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])

        if units > 0 and pending_exit:
            fill = open_price * (1.0 - slippage_rate)
            close_position(
                time=time,
                bar_index=bar_index,
                fill_price=fill,
                reason="smx_exit",
            )
            pending_exit = False

        if units == 0 and pending_entry_atr is not None:
            atr_at_signal = pending_entry_atr
            pending_entry_atr = None
            if np.isfinite(atr_at_signal) and atr_at_signal > 0:
                fill = open_price * (1.0 + slippage_rate)
                stop_distance = config.stop_atr_multiple * atr_at_signal
                max_units_by_weight = config.max_position_weight * cash / fill
                max_units_by_risk = config.risk_fraction * cash / stop_distance
                max_units_by_cash = cash / (fill * (1.0 + commission_rate))
                raw_units = min(
                    max_units_by_weight,
                    max_units_by_risk,
                    max_units_by_cash,
                )
                sized_units = floor(raw_units / config.lot_size) * config.lot_size
                if sized_units > 0:
                    units = float(sized_units)
                    entry_price = float(fill)
                    entry_time = time
                    entry_index = bar_index
                    entry_notional = units * entry_price
                    entry_commission = entry_notional * commission_rate
                    cash -= entry_notional + entry_commission
                    stop_price = entry_price - stop_distance

        if units > 0 and low_price <= stop_price:
            raw_stop_fill = open_price if open_price <= stop_price else stop_price
            fill = raw_stop_fill * (1.0 - slippage_rate)
            close_position(
                time=time,
                bar_index=bar_index,
                fill_price=fill,
                reason="protective_stop",
            )
            pending_exit = False

        if units > 0 and bool(row["exit_signal"]):
            pending_exit = True

        if units == 0 and pending_entry_atr is None and bool(row["entry_signal"]):
            atr_value = float(row["atr"])
            if np.isfinite(atr_value) and atr_value > 0:
                pending_entry_atr = atr_value

        equity = cash + units * close_price
        curve_records.append(
            {
                "cash": float(cash),
                "position_units": float(units),
                "close": close_price,
                "equity": float(equity),
            }
        )

    if units > 0:
        final_time = signals.index[-1]
        final_close = float(signals.iloc[-1]["close"])
        fill = final_close * (1.0 - slippage_rate)
        close_position(
            time=final_time,
            bar_index=len(signals) - 1,
            fill_price=fill,
            reason="end_of_data",
        )
        curve_records[-1]["cash"] = float(cash)
        curve_records[-1]["position_units"] = 0.0
        curve_records[-1]["equity"] = float(cash)

    equity_curve = pd.DataFrame(curve_records, index=signals.index)
    trade_tuple = tuple(trades)
    metrics = _metrics(
        equity_curve["equity"],
        trade_tuple,
        initial_cash=config.initial_cash,
        annualization=config.annualization,
    )
    return BacktestResult(
        equity_curve=equity_curve,
        trades=trade_tuple,
        metrics=metrics,
    )


def run_buy_and_hold(
    data: pd.DataFrame, config: BacktestConfig | None = None
) -> BacktestResult:
    """Run a fully invested buy-and-hold comparator on supplied OHLC bars.

    It enters at the first open and liquidates at the final close, using the
    same commission, slippage, and lot-size assumptions as the strategy.
    """
    config = config or BacktestConfig()
    _validate_config(config)
    missing = sorted({"open", "close"}.difference(data.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    if len(data) < 2:
        raise ValueError("buy-and-hold requires at least two bars")
    commission_rate = config.commission_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0
    entry_price = float(data.iloc[0]["open"]) * (1.0 + slippage_rate)
    if not np.isfinite(entry_price) or entry_price <= 0:
        raise ValueError("first open must be positive and finite")
    units = (
        floor(
            config.initial_cash
            / (entry_price * (1.0 + commission_rate))
            / config.lot_size
        )
        * config.lot_size
    )
    if units <= 0:
        raise ValueError("initial cash cannot purchase one lot")
    entry_commission = units * entry_price * commission_rate
    cash = config.initial_cash - units * entry_price - entry_commission
    curve_records = []
    for _, row in data.iterrows():
        close = float(row["close"])
        curve_records.append(
            {
                "cash": float(cash),
                "position_units": float(units),
                "close": close,
                "equity": float(cash + units * close),
            }
        )
    exit_price = float(data.iloc[-1]["close"]) * (1.0 - slippage_rate)
    exit_commission = units * exit_price * commission_rate
    cash += units * exit_price - exit_commission
    trade = Trade(
        entry_time=data.index[0],
        exit_time=data.index[-1],
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        units=float(units),
        pnl=float(cash - config.initial_cash),
        return_pct=float((cash - config.initial_cash) / config.initial_cash),
        holding_bars=len(data) - 1,
        exit_reason="end_of_data",
    )
    curve_records[-1] = {
        "cash": float(cash),
        "position_units": 0.0,
        "close": float(data.iloc[-1]["close"]),
        "equity": float(cash),
    }
    equity_curve = pd.DataFrame(curve_records, index=data.index)
    return BacktestResult(
        equity_curve=equity_curve,
        trades=(trade,),
        metrics=_metrics(
            equity_curve["equity"],
            (trade,),
            initial_cash=config.initial_cash,
            annualization=config.annualization,
        ),
    )
