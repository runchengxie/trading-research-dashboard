from __future__ import annotations

import json
import math
from collections.abc import Collection, Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

AGENT_PORTFOLIO_VERSION = "trading_research.agent_portfolio.v1"
_SCHEMA_RESOURCE = files("research_core.schemas").joinpath("agent-portfolio.v1.schema.json")
_SCHEMA = json.loads(_SCHEMA_RESOURCE.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)
_WEIGHT_TOLERANCE = 1e-6


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def validate_agent_portfolio(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError("agent portfolio schema validation failed: root must be an object")
    errors = sorted(
        _VALIDATOR.iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(
            "agent portfolio schema validation failed at "
            f"{_error_location(error)}: {error.message}"
        )
    _validate_financial_invariants(payload)


def _validate_financial_invariants(payload: Mapping[str, Any]) -> None:
    portfolio = payload["portfolio"]
    positions = payload["positions"]
    history = payload["history"]
    weights = payload["decision"]["targetWeights"]
    if any(not math.isfinite(float(value)) for value in portfolio.values()):
        raise ValueError("agent portfolio financial invariants failed: non-finite portfolio value")
    if any(not math.isfinite(float(value)) for value in weights.values()):
        raise ValueError("agent portfolio financial invariants failed: non-finite target weight")
    if abs(float(portfolio["equity"]) - (float(portfolio["cash"]) + sum(
        float(position["marketValue"]) for position in positions
    ))) > _WEIGHT_TOLERANCE:
        raise ValueError("agent portfolio financial invariants failed: equity mismatch")
    if abs(float(portfolio["nav"]) - float(portfolio["equity"]) / float(portfolio["initialEquity"])) > _WEIGHT_TOLERANCE:
        raise ValueError("agent portfolio financial invariants failed: nav mismatch")
    if abs(sum(float(value) for value in weights.values()) - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError("agent portfolio financial invariants failed: target weights mismatch")
    if len({position["symbol"] for position in positions}) != len(positions):
        raise ValueError("agent portfolio financial invariants failed: duplicate position")
    history_dates = [point["asOf"] for point in history]
    if history_dates != sorted(set(history_dates)):
        raise ValueError("agent portfolio financial invariants failed: history order")


def load_agent_portfolio(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"agent portfolio schema validation failed: invalid JSON: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise TypeError("agent portfolio schema validation failed: root must be an object")
    validate_agent_portfolio(payload)
    return payload


def validate_target_weights(
    weights: Mapping[str, Any],
    allowed_symbols: Collection[str],
    max_position_weight: float,
    min_cash_weight: float,
) -> dict[str, float]:
    if not isinstance(weights, Mapping) or not weights:
        raise ValueError("target weights must be a non-empty object")
    if not 0 <= min_cash_weight <= 1:
        raise ValueError("minimum cash weight must be between 0 and 1")
    if not 0 < max_position_weight <= 1:
        raise ValueError("maximum position weight must be between 0 and 1")

    allowed = set(allowed_symbols)
    normalized: dict[str, float] = {}
    for symbol, value in weights.items():
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("target weight symbols must be non-empty strings")
        if symbol not in allowed:
            raise ValueError(f"unknown symbol: {symbol}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"target weight must be numeric: {symbol}")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0:
            raise ValueError(f"target weight must be finite and non-negative: {symbol}")
        if symbol != "CASH" and numeric > max_position_weight + _WEIGHT_TOLERANCE:
            raise ValueError(f"maximum position weight exceeded: {symbol}")
        normalized[symbol] = numeric

    risky_total = sum(value for symbol, value in normalized.items() if symbol != "CASH")
    cash = normalized.get("CASH", 0.0)
    if risky_total + cash > 1 + _WEIGHT_TOLERANCE:
        raise ValueError("target weights must not exceed total weight 1")
    normalized["CASH"] = round(max(cash, 1.0 - risky_total), 10)
    if normalized["CASH"] + _WEIGHT_TOLERANCE < min_cash_weight:
        raise ValueError("minimum cash weight not satisfied")
    return normalized
