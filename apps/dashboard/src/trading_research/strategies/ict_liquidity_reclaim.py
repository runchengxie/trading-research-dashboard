"""Objective intraday liquidity-reclaim research rule.

The rule deliberately describes observable price events rather than assigning
causal meaning to them: a bar trades beyond the previous session extreme and
closes back through that level.  It is intended as a small, auditable
benchmark for contextual/ICT hypotheses, not as an ICT-specific score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class LiquidityReclaimConfig:
    """Execution and risk assumptions for one regular US session."""

    stop_buffer_bps: float = 5.0
    target_r: float = 1.5
    slippage_bps: float = 2.0
    session_start: str = "09:30"
    session_end: str = "16:00"

    def __post_init__(self) -> None:
        if self.stop_buffer_bps < 0 or self.target_r <= 0 or self.slippage_bps < 0:
            raise ValueError("risk and execution parameters must be non-negative")


def _iso(timestamp: pd.Timestamp) -> str:
    return timestamp.isoformat()


def _session_bars(bars: pd.DataFrame, config: LiquidityReclaimConfig) -> pd.DataFrame:
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("bars must use a DatetimeIndex")
    normalized = bars.rename(
        columns={"开盘": "open", "最高": "high", "最低": "low", "收盘": "close"}
    )
    required = {"open", "high", "low", "close"}
    missing = required - set(normalized.columns)
    if missing:
        raise ValueError(f"bars missing columns: {', '.join(sorted(missing))}")
    localized = normalized.copy()
    index = localized.index
    if index.tz is None:
        index = index.tz_localize("America/New_York")
    else:
        index = index.tz_convert("America/New_York")
    localized.index = index
    localized = localized.sort_index()
    start = pd.Timestamp(config.session_start).time()
    end = pd.Timestamp(config.session_end).time()
    return localized[(localized.index.time >= start) & (localized.index.time <= end)]


def _net_execution(
    side: str,
    entry_raw: float,
    exit_raw: float,
    slippage_bps: float,
) -> tuple[float, float, float]:
    slip = slippage_bps / 10_000
    if side == "long":
        entry = entry_raw * (1 + slip)
        exit = exit_raw * (1 - slip)
        gross = (exit_raw - entry_raw) / entry_raw
    else:
        entry = entry_raw * (1 - slip)
        exit = exit_raw * (1 + slip)
        gross = (entry_raw - exit_raw) / entry_raw
    net = (exit - entry) / entry if side == "long" else (entry - exit) / entry
    return gross, net, net - gross


def _trade_for_signal(
    session: pd.DataFrame,
    signal_position: int,
    side: str,
    level: float,
    config: LiquidityReclaimConfig,
) -> dict[str, Any] | None:
    if signal_position + 1 >= len(session):
        return None

    signal_time = session.index[signal_position]
    entry_time = session.index[signal_position + 1]
    entry_raw = float(session.iloc[signal_position + 1]["open"])
    signal_bar = session.iloc[signal_position]
    buffer = config.stop_buffer_bps / 10_000
    if side == "long":
        stop = float(signal_bar["low"]) * (1 - buffer)
        risk = entry_raw - stop
        target = entry_raw + config.target_r * risk
    else:
        stop = float(signal_bar["high"]) * (1 + buffer)
        risk = stop - entry_raw
        target = entry_raw - config.target_r * risk
    if risk <= 0:
        return None

    held = session.iloc[signal_position + 1 :].copy()
    exit_raw: float | None = None
    exit_time: pd.Timestamp | None = None
    exit_reason = "session_close"
    for timestamp, bar in held.iterrows():
        if side == "long":
            stop_hit = float(bar["low"]) <= stop
            target_hit = float(bar["high"]) >= target
        else:
            stop_hit = float(bar["high"]) >= stop
            target_hit = float(bar["low"]) <= target
        # OHLC bars cannot reveal the intrabar path. Stop-first is the
        # conservative, deterministic tie-breaker.
        if stop_hit:
            exit_raw, exit_time, exit_reason = stop, timestamp, "stop"
            break
        if target_hit:
            exit_raw, exit_time, exit_reason = target, timestamp, "target"
            break
    if exit_raw is None or exit_time is None:
        exit_time = held.index[-1]
        exit_raw = float(held.iloc[-1]["close"])

    gross, net, cost = _net_execution(side, entry_raw, exit_raw, config.slippage_bps)
    if side == "long":
        mfe = (float(held["high"].max()) - entry_raw) / entry_raw
        mae = (float(held["low"].min()) - entry_raw) / entry_raw
    else:
        mfe = (entry_raw - float(held["low"].min())) / entry_raw
        mae = (entry_raw - float(held["high"].max())) / entry_raw
        mae = -abs(mae)
    return {
        "signalTime": _iso(signal_time),
        "entryTime": _iso(entry_time),
        "exitTime": _iso(exit_time),
        "side": side,
        "referenceLevel": level,
        "entryPrice": entry_raw,
        "exitPrice": exit_raw,
        "stopPrice": stop,
        "targetPrice": target,
        "exitReason": exit_reason,
        "grossReturn": gross,
        "costReturn": cost,
        "netReturn": net,
        "mfe": mfe,
        "mae": mae,
    }


def evaluate_session(
    bars: pd.DataFrame,
    *,
    previous_day_high: float,
    previous_day_low: float,
    config: LiquidityReclaimConfig | None = None,
) -> list[dict[str, Any]]:
    """Evaluate at most one reclaim trade for one regular-session DataFrame."""

    config = config or LiquidityReclaimConfig()
    if previous_day_high <= 0 or previous_day_low <= 0 or previous_day_high <= previous_day_low:
        raise ValueError("previous day levels must be positive and ordered")
    session = _session_bars(bars, config)
    if session.empty:
        return []
    for position in range(len(session) - 1):
        bar = session.iloc[position]
        if float(bar["low"]) < previous_day_low and float(bar["close"]) > previous_day_low:
            trade = _trade_for_signal(session, position, "long", previous_day_low, config)
            return [] if trade is None else [trade]
        if float(bar["high"]) > previous_day_high and float(bar["close"]) < previous_day_high:
            trade = _trade_for_signal(session, position, "short", previous_day_high, config)
            return [] if trade is None else [trade]
    return []


def run_liquidity_reclaim(
    bars: pd.DataFrame,
    *,
    previous_day_high: float,
    previous_day_low: float,
    config: LiquidityReclaimConfig | None = None,
) -> dict[str, Any]:
    """Return trades and transparent summary metrics for one session."""

    trades = evaluate_session(
        bars,
        previous_day_high=previous_day_high,
        previous_day_low=previous_day_low,
        config=config,
    )
    returns = pd.Series([float(trade["netReturn"]) for trade in trades], dtype=float)
    gross = sum(float(trade["grossReturn"]) for trade in trades)
    net = sum(float(trade["netReturn"]) for trade in trades)
    win_rate = float((returns > 0).mean()) if not returns.empty else None
    profit_factor = None
    losses = returns[returns < 0].sum()
    if losses < 0:
        profit_factor = float(returns[returns > 0].sum() / abs(losses))
    return {
        "trades": trades,
        "entry_signal_count": len(trades),
        "gross_return": gross,
        "net_return": net,
        "cost_return": net - gross,
        "trade_count": len(trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "mfe": float(returns.mean()) if not returns.empty else None,
        "mae": None,
        "annualized_return": None,
        "sharpe": None,
    }
