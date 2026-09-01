from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from research_core.agent_portfolio import validate_target_weights


@dataclass(frozen=True)
class Position:
    symbol: str
    shares: int
    price: float
    market_value: float


@dataclass(frozen=True)
class Trade:
    timestamp: str
    symbol: str
    side: str
    shares: int
    price: float
    fee: float


@dataclass(frozen=True)
class PaperPortfolioState:
    as_of: str
    initial_equity: float
    equity: float
    cash: float
    positions: dict[str, Position]
    history: tuple[dict[str, Any], ...]
    trades: tuple[Trade, ...]


def simulate_rebalance(
    previous: PaperPortfolioState | None,
    target_weights: dict[str, float],
    prices: dict[str, float],
    as_of: str,
    initial_equity: float,
    fee_rate: float,
    max_position_weight: float,
    min_cash_weight: float,
    *,
    lot_size: int = 1,
    stamp_duty_rate: float = 0.0,
    stock_symbols: set[str] | None = None,
    previous_closes: dict[str, float] | None = None,
    limit_up_down_pct: float | None = None,
) -> PaperPortfolioState:
    if previous is not None and as_of <= previous.as_of:
        raise ValueError("as_of must be after previous portfolio date")
    if initial_equity <= 0 or not math.isfinite(initial_equity):
        raise ValueError("initial equity must be positive and finite")
    if fee_rate < 0 or not math.isfinite(fee_rate):
        raise ValueError("fee rate must be non-negative and finite")
    if lot_size <= 0:
        raise ValueError("lot size must be positive")
    if stamp_duty_rate < 0 or not math.isfinite(stamp_duty_rate):
        raise ValueError("stamp duty rate must be non-negative and finite")
    if limit_up_down_pct is not None and (
        limit_up_down_pct <= 0 or not math.isfinite(limit_up_down_pct)
    ):
        raise ValueError("limit percentage must be positive and finite")
    if not prices:
        raise ValueError("prices must not be empty")
    for symbol, price in prices.items():
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            raise ValueError(f"price must be numeric: {symbol}")
        if not math.isfinite(float(price)) or float(price) <= 0:
            raise ValueError(f"price must be positive and finite: {symbol}")

    previous_positions = previous.positions if previous else {}
    missing = sorted(set(previous_positions) - prices.keys())
    if missing:
        raise ValueError(f"missing price: {', '.join(missing)}")
    allowed_symbols = set(prices) | set(previous_positions) | {"CASH"}
    normalized = validate_target_weights(
        target_weights,
        allowed_symbols,
        max_position_weight=max_position_weight,
        min_cash_weight=min_cash_weight,
    )

    cash = previous.cash if previous else initial_equity
    current_equity = cash + sum(
        position.shares * float(prices[symbol]) for symbol, position in previous_positions.items()
    )
    if current_equity <= 0:
        raise ValueError("current equity must be positive")
    target_shares = {
        symbol: math.floor(current_equity * weight / float(prices[symbol]) / lot_size) * lot_size
        for symbol, weight in normalized.items()
        if symbol != "CASH"
    }
    trades: list[Trade] = []
    shares = {symbol: position.shares for symbol, position in previous_positions.items()}

    for symbol in sorted(set(shares) | set(target_shares)):
        sell_shares = max(0, shares.get(symbol, 0) - target_shares.get(symbol, 0))
        if sell_shares == 0:
            continue
        price = float(prices[symbol])
        if _blocked_by_limit(
            symbol, price, previous_closes, limit_up_down_pct, direction="sell"
        ):
            continue
        fee = sell_shares * price * (fee_rate + (stamp_duty_rate if symbol in (stock_symbols or set()) else 0.0))
        cash += sell_shares * price - fee
        shares[symbol] -= sell_shares
        trades.append(Trade(as_of, symbol, "SELL", sell_shares, price, fee))

    for symbol in sorted(target_shares):
        buy_shares = max(0, target_shares[symbol] - shares.get(symbol, 0))
        if buy_shares == 0:
            continue
        price = float(prices[symbol])
        if _blocked_by_limit(
            symbol, price, previous_closes, limit_up_down_pct, direction="buy"
        ):
            continue
        affordable = math.floor(cash / (price * (1 + fee_rate)))
        executed = min(buy_shares, affordable // lot_size * lot_size)
        if executed == 0:
            continue
        fee = executed * price * fee_rate
        cash -= executed * price + fee
        shares[symbol] = shares.get(symbol, 0) + executed
        trades.append(Trade(as_of, symbol, "BUY", executed, price, fee))

    positions = {
        symbol: Position(symbol, quantity, float(prices[symbol]), quantity * float(prices[symbol]))
        for symbol, quantity in sorted(shares.items())
        if quantity > 0
    }
    equity = cash + sum(position.market_value for position in positions.values())
    old_high = max(
        (float(point["equity"]) for point in (previous.history if previous else ())),
        default=initial_equity,
    )
    high_water = max(old_high, equity)
    drawdown = equity / high_water - 1.0
    history = (
        previous.history if previous else ()
    ) + ({"asOf": as_of, "equity": equity, "nav": equity / initial_equity, "drawdown": drawdown},)
    return PaperPortfolioState(
        as_of=as_of,
        initial_equity=initial_equity,
        equity=equity,
        cash=cash,
        positions=positions,
        history=history,
        trades=tuple(trades),
    )


def _blocked_by_limit(
    symbol: str,
    price: float,
    previous_closes: dict[str, float] | None,
    limit_up_down_pct: float | None,
    *,
    direction: str,
) -> bool:
    if limit_up_down_pct is None or not previous_closes or symbol not in previous_closes:
        return False
    previous = float(previous_closes[symbol])
    if direction == "buy":
        return price >= previous * (1 + limit_up_down_pct)
    return price <= previous * (1 - limit_up_down_pct)
