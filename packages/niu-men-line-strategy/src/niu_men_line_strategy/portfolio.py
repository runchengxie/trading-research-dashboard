"""Cross-sectional portfolio backtesting for synchronized daily signals."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import floor
from typing import Any

import numpy as np
import pandas as pd

from .backtest import BacktestConfig, performance_metrics


@dataclass(frozen=True)
class PortfolioTrade:
    symbol: str
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    units: float
    gross_pnl: float
    pnl: float
    return_pct: float
    holding_bars: int
    exit_reason: str
    commission: float
    slippage_cost: float


@dataclass(frozen=True)
class PortfolioResult:
    equity_curve: pd.DataFrame
    trades: tuple[PortfolioTrade, ...]
    metrics: dict[str, float]


@dataclass
class _Position:
    symbol: str
    entry_time: Any
    entry_price: float
    entry_reference_price: float
    units: float
    entry_commission: float
    stop_price: float
    bars_held: int = 0
    pending_exit: bool = False
    pending_stop: bool = False


_REQUIRED_COLUMNS = {
    "open",
    "high",
    "low",
    "close",
    "atr",
    "entry_signal",
    "exit_signal",
}


def _validate_frames(frames: dict[str, pd.DataFrame]) -> None:
    if not frames:
        raise ValueError("portfolio requires at least one symbol")
    for symbol, frame in frames.items():
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("portfolio symbols must be non-empty strings")
        if not isinstance(frame.index, pd.DatetimeIndex):
            raise TypeError(f"{symbol} data index must be a DatetimeIndex")
        if frame.empty:
            raise ValueError(f"{symbol} data cannot be empty")
        missing = sorted(_REQUIRED_COLUMNS.difference(frame.columns))
        if missing:
            raise ValueError(f"{symbol} data missing columns: {', '.join(missing)}")
        if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
            raise ValueError(f"{symbol} dates must be unique and ascending")


def _limit_blocked(limit: float, open_price: float) -> bool:
    return bool(np.isfinite(limit) and np.isclose(open_price, limit))


def _mark_equity(
    cash: float,
    positions: dict[str, _Position],
    bars: dict[str, tuple[float, ...]],
    last_close: dict[str, float],
    price_index: int,
) -> float:
    equity = cash
    for symbol, position in positions.items():
        row = bars.get(symbol)
        if row is not None:
            price = row[price_index]
            last_close[symbol] = row[3]
        else:
            price = last_close[symbol]
        equity += position.units * price
    return float(equity)


def run_portfolio_backtest(
    signal_frames: dict[str, pd.DataFrame],
    config: BacktestConfig | None = None,
) -> PortfolioResult:
    """Run a long-only portfolio with close-confirmed next-open execution.

    Each input frame represents one symbol. Signals on a symbol's bar ``t``
    execute on that symbol's next available bar. Entries compete for shared
    cash, while the position and risk caps are applied per symbol. Portfolio
    equity is marked at each date in the union of all symbol calendars.
    """

    _validate_frames(signal_frames)
    config = config or BacktestConfig()
    commission_rate = config.commission_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0

    bars_by_date: dict[pd.Timestamp, dict[str, tuple[float, ...]]] = defaultdict(dict)
    entry_events: dict[pd.Timestamp, list[tuple[str, float]]] = defaultdict(list)
    exit_events: dict[pd.Timestamp, list[str]] = defaultdict(list)
    last_date: dict[str, pd.Timestamp] = {}
    for symbol, frame in signal_frames.items():
        dates = list(frame.index)
        last_date[symbol] = dates[-1]
        columns = {column: frame.columns.get_loc(column) for column in frame.columns}
        open_index = columns["open"] + 1
        high_index = columns["high"] + 1
        low_index = columns["low"] + 1
        close_index = columns["close"] + 1
        atr_index = columns["atr"] + 1
        entry_index = columns["entry_signal"] + 1
        exit_index = columns["exit_signal"] + 1
        up_limit_index = columns.get("up_limit")
        up_limit_index = up_limit_index + 1 if up_limit_index is not None else None
        down_limit_index = columns.get("down_limit")
        down_limit_index = down_limit_index + 1 if down_limit_index is not None else None
        for index, values in enumerate(frame.itertuples(index=True, name=None)):
            date = values[0]
            bar = (
                float(values[open_index]),
                float(values[high_index]),
                float(values[low_index]),
                float(values[close_index]),
                float(values[atr_index]),
                float(values[up_limit_index]) if up_limit_index is not None else float("nan"),
                float(values[down_limit_index]) if down_limit_index is not None else float("nan"),
            )
            bars_by_date[date][symbol] = bar
            if index + 1 >= len(dates):
                continue
            next_date = dates[index + 1]
            if bool(values[entry_index]):
                entry_events[next_date].append((symbol, bar[4]))
            if bool(values[exit_index]):
                exit_events[next_date].append(symbol)

    cash = float(config.initial_cash)
    positions: dict[str, _Position] = {}
    last_close: dict[str, float] = {}
    trades: list[PortfolioTrade] = []
    curve_records: list[dict[str, float]] = []
    blocked_entries = 0
    blocked_exit_days = 0
    blocked_smx_exits = 0
    blocked_stop_exits = 0
    total_turnover = 0.0
    total_commission = 0.0
    total_slippage = 0.0

    def close_position(
        symbol: str,
        time: pd.Timestamp,
        reference_price: float,
        reason: str,
    ) -> None:
        nonlocal cash, total_turnover, total_commission, total_slippage
        position = positions.pop(symbol)
        fill_price = reference_price * (1.0 - slippage_rate)
        exit_notional = position.units * fill_price
        exit_commission = exit_notional * commission_rate
        commission = position.entry_commission + exit_commission
        gross_pnl = (reference_price - position.entry_reference_price) * position.units
        pnl = (fill_price - position.entry_price) * position.units - commission
        slippage_cost = (
            abs(position.entry_price - position.entry_reference_price) * position.units
            + abs(fill_price - reference_price) * position.units
        )
        cash += exit_notional - exit_commission
        total_turnover += position.entry_price * position.units + exit_notional
        # Entry commission was charged when the position opened. Add only the
        # exit leg here so portfolio totals remain accurate.
        total_commission += exit_commission
        total_slippage += slippage_cost
        invested = position.entry_price * position.units + position.entry_commission
        trades.append(
            PortfolioTrade(
                symbol=symbol,
                entry_time=position.entry_time,
                exit_time=time,
                entry_price=position.entry_price,
                exit_price=fill_price,
                units=position.units,
                gross_pnl=float(gross_pnl),
                pnl=float(pnl),
                return_pct=float(pnl / invested) if invested else float("nan"),
                holding_bars=position.bars_held,
                exit_reason=reason,
                commission=float(commission),
                slippage_cost=float(slippage_cost),
            )
        )

    for date in sorted(bars_by_date):
        bars = bars_by_date[date]
        for symbol, row in bars.items():
            last_close[symbol] = row[3]

        for symbol in exit_events.get(date, []):
            if symbol in positions:
                positions[symbol].pending_exit = True

        blocked_today: set[str] = set()
        blocked_exit_today = False
        for symbol in sorted(positions):
            position = positions[symbol]
            row = bars.get(symbol)
            if row is None or not position.pending_exit:
                continue
            open_price = row[0]
            if _limit_blocked(row[6], open_price):
                blocked_today.add(symbol)
                blocked_exit_today = True
                blocked_smx_exits += 1
            else:
                close_position(symbol, date, open_price, "smx_exit")

        for symbol, atr_at_signal in sorted(entry_events.get(date, [])):
            if symbol in positions:
                continue
            row = bars.get(symbol)
            if row is None:
                continue
            open_price = row[0]
            if _limit_blocked(row[5], open_price):
                blocked_entries += 1
                continue
            if not np.isfinite(atr_at_signal) or atr_at_signal <= 0:
                continue
            equity = _mark_equity(cash, positions, bars, last_close, 0)
            fill_price = open_price * (1.0 + slippage_rate)
            stop_distance = config.stop_atr_multiple * atr_at_signal
            max_by_weight = config.max_position_weight * equity / fill_price
            max_by_risk = config.risk_fraction * equity / stop_distance
            max_by_cash = cash / (fill_price * (1.0 + commission_rate))
            raw_units = min(max_by_weight, max_by_risk, max_by_cash)
            units = floor(raw_units / config.lot_size) * config.lot_size
            if units <= 0:
                continue
            entry_notional = units * fill_price
            entry_commission = entry_notional * commission_rate
            cash -= entry_notional + entry_commission
            total_commission += entry_commission
            positions[symbol] = _Position(
                symbol=symbol,
                entry_time=date,
                entry_price=fill_price,
                entry_reference_price=open_price,
                units=float(units),
                entry_commission=entry_commission,
                stop_price=fill_price - stop_distance,
            )

        for symbol in sorted(positions):
            position = positions[symbol]
            row = bars.get(symbol)
            if row is None:
                continue
            if position.entry_time != date:
                position.bars_held += 1
            open_price = row[0]
            low_price = row[2]
            if position.pending_stop or low_price <= position.stop_price:
                if _limit_blocked(row[6], open_price):
                    position.pending_stop = True
                    if symbol not in blocked_today:
                        blocked_today.add(symbol)
                        blocked_exit_today = True
                    blocked_stop_exits += 1
                else:
                    raw_stop_fill = min(open_price, position.stop_price)
                    close_position(symbol, date, raw_stop_fill, "protective_stop")
                    continue

        for symbol, row in bars.items():
            if date != last_date[symbol]:
                continue
            if symbol in positions:
                close_position(
                    symbol,
                    date,
                    row[3],
                    "end_of_data",
                )

        equity = _mark_equity(cash, positions, bars, last_close, 3)
        if blocked_exit_today:
            blocked_exit_days += 1
        curve_records.append(
            {
                "cash": float(cash),
                "position_count": float(len(positions)),
                "equity": float(equity),
            }
        )

    equity_curve = pd.DataFrame(curve_records, index=pd.DatetimeIndex(sorted(bars_by_date)))
    metrics = performance_metrics(
        equity_curve["equity"],
        tuple(trades),
        initial_cash=config.initial_cash,
        annualization=config.annualization,
    )
    metrics.update(
        {
            "blocked_entry_count": float(blocked_entries),
            "blocked_exit_day_count": float(blocked_exit_days),
            "blocked_smx_exit_day_count": float(blocked_smx_exits),
            "blocked_stop_exit_day_count": float(blocked_stop_exits),
            "commission_paid": float(total_commission),
            "slippage_cost": float(total_slippage),
            "turnover": float(total_turnover / config.initial_cash),
            "position_count_max": float(equity_curve["position_count"].max()),
        }
    )
    return PortfolioResult(equity_curve, tuple(trades), metrics)


def run_equal_weight_buy_and_hold(
    frames: dict[str, pd.DataFrame],
    config: BacktestConfig | None = None,
) -> PortfolioResult:
    """Buy each symbol once with an equal initial cash budget and hold it."""

    _validate_frames(frames)
    config = config or BacktestConfig()
    commission_rate = config.commission_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0
    symbols = sorted(frames)
    budget = config.initial_cash / len(symbols)
    cash = float(config.initial_cash)
    entries: dict[str, tuple[pd.Timestamp, float, float, float]] = {}
    for symbol in symbols:
        frame = frames[symbol]
        date = frame.index[0]
        row = frame.iloc[0]
        open_price = float(row["open"])
        up_limit = float(row["up_limit"]) if "up_limit" in frame else float("nan")
        if _limit_blocked(up_limit, open_price):
            continue
        fill_price = open_price * (1.0 + slippage_rate)
        units = floor(budget / (fill_price * (1.0 + commission_rate)) / config.lot_size)
        units *= config.lot_size
        if units <= 0:
            continue
        commission = units * fill_price * commission_rate
        cash -= units * fill_price + commission
        entries[symbol] = (date, fill_price, units, commission)

    entry_cash = cash
    dates = sorted(set().union(*(frame.index for frame in frames.values())))
    exit_cash_by_date: dict[pd.Timestamp, float] = defaultdict(float)
    trades: list[PortfolioTrade] = []
    for symbol, (entry_date, entry_price, units, entry_commission) in entries.items():
        frame = frames[symbol]
        row = frame.iloc[-1]
        reference_exit = float(row["close"])
        exit_price = reference_exit * (1.0 - slippage_rate)
        exit_commission = units * exit_price * commission_rate
        exit_cash_by_date[frame.index[-1]] += units * exit_price - exit_commission
        commission = entry_commission + exit_commission
        pnl = (exit_price - entry_price) * units - commission
        gross_pnl = (reference_exit - float(frame.iloc[0]["open"])) * units
        trades.append(
            PortfolioTrade(
                symbol=symbol,
                entry_time=entry_date,
                exit_time=frame.index[-1],
                entry_price=entry_price,
                exit_price=exit_price,
                units=units,
                gross_pnl=float(gross_pnl),
                pnl=float(pnl),
                return_pct=float(pnl / (entry_price * units + entry_commission)),
                holding_bars=max(len(frame) - 1, 0),
                exit_reason="end_of_data",
                commission=float(commission),
                slippage_cost=float(
                    abs(entry_price - float(frame.iloc[0]["open"])) * units
                    + abs(exit_price - reference_exit) * units
                ),
            )
        )

    date_index = pd.DatetimeIndex(dates)
    cash_flows = pd.Series(
        [exit_cash_by_date.get(date, 0.0) for date in date_index],
        index=date_index,
        dtype=float,
    )
    cash_curve = entry_cash + cash_flows.cumsum()
    holding_columns: dict[str, pd.Series] = {}
    position_count = pd.Series(0.0, index=date_index)
    for symbol, (entry_date, _, units, _) in entries.items():
        frame = frames[symbol]
        close = frame["close"].reindex(date_index).ffill()
        held = (date_index >= entry_date) & (date_index < frame.index[-1])
        holding_columns[symbol] = close.where(held, 0.0) * units
        position_count += held.astype(float)
    holdings = (
        pd.concat(holding_columns, axis=1) if holding_columns else pd.DataFrame(index=date_index)
    )
    holding_value = holdings.sum(axis=1) if not holdings.empty else pd.Series(0.0, index=date_index)
    equity_curve = pd.DataFrame(
        {
            "cash": cash_curve,
            "position_count": position_count,
            "equity": cash_curve + holding_value,
        },
        index=date_index,
    )
    metrics = performance_metrics(
        equity_curve["equity"],
        tuple(trades),
        initial_cash=config.initial_cash,
        annualization=config.annualization,
    )
    metrics.update(
        {
            "commission_paid": float(sum(trade.commission for trade in trades)),
            "slippage_cost": float(sum(trade.slippage_cost for trade in trades)),
            "turnover": float(
                sum(
                    trade.entry_price * trade.units + trade.exit_price * trade.units
                    for trade in trades
                )
                / config.initial_cash
            ),
            "position_count_max": float(len(entries)),
            "blocked_entry_count": float(len(frames) - len(entries)),
            "blocked_exit_day_count": 0.0,
            "blocked_smx_exit_day_count": 0.0,
            "blocked_stop_exit_day_count": 0.0,
        }
    )
    return PortfolioResult(equity_curve, tuple(trades), metrics)
