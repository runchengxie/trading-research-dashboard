"""Translate Niu Men signals into the portfolio backtester input contract.

The adapter deliberately stops at a target-position schedule. The Niu Men
engine remains the source of truth for ATR sizing, protective stops, and
price-limit retry behavior; those event-driven rules are not inferred from a
position schedule here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd

__all__ = ["PortfolioReplayInputs", "build_portfolio_replay_inputs"]

_REQUIRED_SIGNAL_COLUMNS = {"close", "entry_signal", "exit_signal"}
_OPTIONAL_PRICING_COLUMNS = ("tradable", "up_limit", "down_limit")


@dataclass(frozen=True)
class PortfolioReplayInputs:
    """Contract-shaped inputs for ``portfolio-backtester``.

    ``positions`` and ``periods`` retain the signal date separately from the
    first executable session. This keeps Niu Men close-confirmed, next-session
    entry timing explicit when the data crosses the repository boundary.
    """

    positions: pd.DataFrame
    pricing: pd.DataFrame
    periods: pd.DataFrame

    def to_payload(self) -> dict[str, list[dict[str, Any]]]:
        """Return deterministic JSON-compatible records for golden artifacts."""

        return {
            "positions": _json_records(self.positions),
            "pricing": _json_records(self.pricing),
            "periods": _json_records(self.periods),
        }


def build_portfolio_replay_inputs(
    signals: pd.DataFrame,
    symbol: str,
    *,
    weight: float = 1.0,
    entry_price_col: str = "open",
    exit_price_col: str = "open",
    final_exit_price_col: str = "close",
) -> PortfolioReplayInputs:
    """Build target-position replay inputs from a single-symbol signal frame.

    Signals observed on session ``t`` are represented as an entry or exit on
    the next available session. An open position is liquidated on the final
    session, matching the Niu Men engine's end-of-data behavior. The result is
    suitable for ``portfolio_backtester.run_position_backtest`` when the
    caller selects ``entry_price`` and ``exit_price`` explicitly.

    This function does not recreate Niu Men's ATR sizing, protective stops, or
    limit-up/limit-down retry state. Optional market-rule columns are carried
    into ``pricing`` so a downstream execution-aware backend can consume them.
    """

    symbol = str(symbol).strip()
    if not symbol:
        raise ValueError("symbol must not be empty")
    if not np.isfinite(weight) or weight <= 0:
        raise ValueError("weight must be finite and positive")
    if not entry_price_col or not exit_price_col or not final_exit_price_col:
        raise ValueError("price column names must not be empty")

    work = _normalise_signals(signals)
    required_price_columns = {entry_price_col, exit_price_col, final_exit_price_col}
    missing_prices = sorted(required_price_columns.difference(work.columns))
    if missing_prices:
        raise ValueError(f"missing required price columns: {', '.join(missing_prices)}")

    price_columns = required_price_columns | {"close"}
    for column in price_columns:
        values = pd.to_numeric(work[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"price column must contain finite numeric values: {column}")
        work[column] = values.astype(float)

    dates = pd.DatetimeIndex(work.index)
    period_records: list[dict[str, Any]] = []
    pending_entry_date: pd.Timestamp | None = None
    pending_exit_date: pd.Timestamp | None = None
    open_trade: dict[str, Any] | None = None

    for row_index in range(len(work)):
        timestamp = cast(pd.Timestamp, dates[row_index])
        row = work.iloc[row_index]

        if open_trade is not None and pending_exit_date is not None:
            period_records.append(
                _close_period(
                    open_trade,
                    exit_date=timestamp,
                    exit_signal_date=pending_exit_date,
                    exit_reason="exit_signal",
                )
            )
            open_trade = None
            pending_exit_date = None

        if open_trade is None and pending_entry_date is not None:
            open_trade = {
                "rebalance_date": pending_entry_date,
                "entry_date": timestamp,
                "entry_signal_date": pending_entry_date,
            }
            pending_entry_date = None

        if open_trade is not None:
            if _signal_is_true(row["exit_signal"]):
                pending_exit_date = timestamp
        elif pending_entry_date is None and _signal_is_true(row["entry_signal"]):
            pending_entry_date = timestamp

    if open_trade is not None:
        period_records.append(
            _close_period(
                open_trade,
                exit_date=dates[-1],
                exit_signal_date=None,
                exit_reason="end_of_data",
            )
        )

    periods = pd.DataFrame(
        period_records,
        columns=[
            "rebalance_date",
            "entry_date",
            "exit_date",
            "planned_exit_date",
            "entry_signal_date",
            "exit_signal_date",
            "exit_reason",
        ],
    )
    if not periods.empty:
        for column in (
            "rebalance_date",
            "entry_date",
            "exit_date",
            "planned_exit_date",
            "entry_signal_date",
            "exit_signal_date",
        ):
            periods[column] = pd.to_datetime(periods[column])

    positions = pd.DataFrame(
        [
            {
                "rebalance_date": period["rebalance_date"],
                "entry_date": period["entry_date"],
                "symbol": symbol,
                "weight": float(weight),
                "side": "long",
                "signal": "entry_signal",
            }
            for period in period_records
        ],
        columns=["rebalance_date", "entry_date", "symbol", "weight", "side", "signal"],
    )
    if not positions.empty:
        positions["rebalance_date"] = pd.to_datetime(positions["rebalance_date"])
        positions["entry_date"] = pd.to_datetime(positions["entry_date"])

    pricing_columns = [
        "trade_date",
        "symbol",
        "close",
        "entry_price",
        "exit_price",
        *_OPTIONAL_PRICING_COLUMNS,
    ]
    pricing_records: list[dict[str, Any]] = []
    for position_index in range(len(work)):
        date = cast(pd.Timestamp, dates[position_index])
        row = work.iloc[position_index]
        record: dict[str, Any] = {
            "trade_date": pd.Timestamp(date),
            "symbol": symbol,
            "close": float(row["close"]),
            "entry_price": float(row[entry_price_col]),
            "exit_price": float(row[exit_price_col]),
        }
        if position_index == len(work) - 1:
            record["exit_price"] = float(row[final_exit_price_col])
        for column in _OPTIONAL_PRICING_COLUMNS:
            if column in work.columns:
                value = row[column]
                record[column] = value.item() if isinstance(value, np.generic) else value
        pricing_records.append(record)

    pricing = pd.DataFrame(pricing_records, columns=pricing_columns)
    pricing["trade_date"] = pd.to_datetime(pricing["trade_date"])
    return PortfolioReplayInputs(positions=positions, pricing=pricing, periods=periods)


def _normalise_signals(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        raise ValueError("signals cannot be empty")
    missing = sorted(_REQUIRED_SIGNAL_COLUMNS.difference(signals.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    work = signals.copy()
    try:
        parsed_index = pd.to_datetime(work.index, errors="coerce")
        normalized_index = pd.DatetimeIndex(
            [
                cast(pd.Timestamp, value).normalize() if not pd.isna(value) else pd.NaT
                for value in parsed_index
            ]
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("signals index must contain valid dates") from exc
    if normalized_index.hasnans:
        raise ValueError("signals index must contain valid dates")
    if not normalized_index.is_unique or not normalized_index.is_monotonic_increasing:
        raise ValueError("signals index must be unique and monotonic")
    work.index = normalized_index
    return work


def _signal_is_true(value: object) -> bool:
    if pd.isna(value):
        return False
    return bool(value)


def _close_period(
    open_trade: dict[str, Any],
    *,
    exit_date: pd.Timestamp,
    exit_signal_date: pd.Timestamp | None,
    exit_reason: str,
) -> dict[str, Any]:
    return {
        **open_trade,
        "exit_date": exit_date,
        "planned_exit_date": exit_date,
        "exit_signal_date": exit_signal_date if exit_signal_date is not None else pd.NaT,
        "exit_reason": exit_reason,
    }


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_record in frame.to_dict(orient="records"):
        record: dict[str, Any] = {}
        for key, value in raw_record.items():
            if pd.isna(value):
                record[key] = None
            elif isinstance(value, pd.Timestamp):
                record[key] = value.date().isoformat()
            elif isinstance(value, pd.Timedelta):
                record[key] = value.isoformat()
            elif isinstance(value, np.generic):
                record[key] = value.item()
            else:
                record[key] = value
        records.append(record)
    return records
