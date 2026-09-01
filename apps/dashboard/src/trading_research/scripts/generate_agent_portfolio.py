from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_core.agent_portfolio import load_agent_portfolio, validate_agent_portfolio

from trading_research.agent_decision import (
    AgentDecision,
    GLMModelClient,
    build_input_hash,
    parse_model_response,
)
from trading_research.agent_portfolio import (
    PaperPortfolioState,
    Position,
    Trade,
    simulate_rebalance,
)

DEFAULT_INITIAL_EQUITY = 100_000.0
DEFAULT_FEE_RATE = 0.001
DEFAULT_MAX_POSITION_WEIGHT = 0.8
DEFAULT_MIN_CASH_WEIGHT = 0.1
DEFAULT_PROMPT_VERSION = "agent-paper-v1"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON input: {path}: {exc.msg}") from exc


def _state_from_payload(payload: dict[str, Any]) -> PaperPortfolioState:
    positions = {
        item["symbol"]: Position(
            symbol=item["symbol"],
            shares=int(item["shares"]),
            price=float(item["price"]),
            market_value=float(item["marketValue"]),
        )
        for item in payload["positions"]
    }
    trades = tuple(
        Trade(
            timestamp=item["timestamp"],
            symbol=item["symbol"],
            side=item["side"],
            shares=int(item["shares"]),
            price=float(item["price"]),
            fee=float(item["fee"]),
        )
        for item in payload["trades"]
    )
    return PaperPortfolioState(
        as_of=payload["asOf"],
        initial_equity=float(payload["portfolio"]["initialEquity"]),
        equity=float(payload["portfolio"]["equity"]),
        cash=float(payload["portfolio"]["cash"]),
        positions=positions,
        history=tuple(payload["history"]),
        trades=trades,
    )


def _state_payload(state: PaperPortfolioState) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positions = [
        {
            "symbol": position.symbol,
            "shares": position.shares,
            "price": position.price,
            "marketValue": position.market_value,
            "weight": position.market_value / state.equity if state.equity else 0.0,
        }
        for position in state.positions.values()
    ]
    trades = [
        {
            "timestamp": trade.timestamp,
            "symbol": trade.symbol,
            "side": trade.side,
            "shares": trade.shares,
            "price": trade.price,
            "fee": trade.fee,
        }
        for trade in state.trades
    ]
    return positions, trades


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            json.dump(payload, temporary, ensure_ascii=False, indent=2, allow_nan=False)
            temporary.write("\n")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _decision_from_input(
    model_response_path: Path | None,
    api_key: str | None,
    context: dict[str, Any],
    allowed_symbols: set[str],
    prompt_version: str,
) -> AgentDecision:
    if model_response_path is not None:
        raw = model_response_path.read_text(encoding="utf-8")
        parsed = parse_model_response(raw, allowed_symbols)
        return AgentDecision(
            target_weights=parsed.target_weights,
            reasoning_summary=parsed.reasoning_summary,
            provider="zhipu",
            model="glm-4.7-flash",
            prompt_version=prompt_version,
            input_hash=build_input_hash(context),
        )
    if not api_key:
        raise ValueError("ZHIPU_API_KEY is required when --model-response is not provided")
    return GLMModelClient(api_key).complete_decision(context, prompt_version, allowed_symbols)


def generate_snapshot(
    prices_path: Path,
    previous_path: Path,
    model_response_path: Path | None,
    output: Path,
    as_of: str,
    generated_at: str,
    api_key: str | None = None,
    allowed_symbols: set[str] | None = None,
) -> dict[str, Any]:
    prices_payload = _read_json(prices_path)
    prices = prices_payload.get("prices", prices_payload) if isinstance(prices_payload, dict) else None
    if not isinstance(prices, dict):
        raise ValueError("prices input must be an object or an object with a prices field")
    previous_payload = load_agent_portfolio(previous_path)
    previous = _state_from_payload(previous_payload)
    symbols = set(prices) | set(previous.positions)
    if allowed_symbols is not None:
        symbols &= set(allowed_symbols)
    symbols.add("CASH")
    context = {
        "asOf": as_of,
        "prices": prices,
        "portfolio": {
            "equity": previous.equity,
            "cash": previous.cash,
            "positions": {
                symbol: position.shares for symbol, position in previous.positions.items()
            },
        },
    }
    decision = _decision_from_input(
        model_response_path,
        api_key,
        context,
        symbols | {"CASH"},
        DEFAULT_PROMPT_VERSION,
    )
    state = simulate_rebalance(
        previous,
        decision.target_weights,
        {symbol: float(value) for symbol, value in prices.items()},
        as_of,
        previous.initial_equity,
        DEFAULT_FEE_RATE,
        DEFAULT_MAX_POSITION_WEIGHT,
        DEFAULT_MIN_CASH_WEIGHT,
    )
    positions, trades = _state_payload(state)
    max_drawdown = min((float(point["drawdown"]) for point in state.history), default=0.0)
    payload = {
        "schemaVersion": "trading_research.agent_portfolio.v1",
        "generatedAt": generated_at,
        "asOf": as_of,
        "agent": {
            "id": "glm-daily",
            "provider": decision.provider,
            "model": decision.model,
            "promptVersion": decision.prompt_version,
            "inputHash": decision.input_hash,
        },
        "portfolio": {
            "initialEquity": state.initial_equity,
            "equity": state.equity,
            "cash": state.cash,
            "nav": state.equity / state.initial_equity,
            "totalReturn": state.equity / state.initial_equity - 1.0,
            "maxDrawdown": max_drawdown,
        },
        "metrics": {"totalReturn": state.equity / state.initial_equity - 1.0, "maxDrawdown": max_drawdown},
        "decision": {
            "targetWeights": decision.target_weights,
            "reasoningSummary": decision.reasoning_summary,
        },
        "positions": positions,
        "trades": trades,
        "history": list(state.history),
    }
    validate_agent_portfolio(payload)
    _write_json_atomic(output, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a validated Agent paper portfolio snapshot")
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--model-response", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--generated-at", default=datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    payload = generate_snapshot(
        prices_path=args.prices,
        previous_path=args.previous,
        model_response_path=args.model_response,
        output=args.output,
        as_of=args.as_of,
        generated_at=args.generated_at,
        api_key=os.environ.get("ZHIPU_API_KEY"),
    )
    print(json.dumps(payload["portfolio"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
