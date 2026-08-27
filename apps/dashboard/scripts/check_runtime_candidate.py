#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty date string")
    raw = value.strip()[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must start with YYYY-MM-DD, got {value!r}") from exc


def _stock_map(snapshot: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    stocks = snapshot.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise ValueError(f"{label}.stocks must contain at least one instrument")

    result: dict[str, dict[str, Any]] = {}
    for index, stock in enumerate(stocks):
        if not isinstance(stock, dict):
            raise ValueError(f"{label}.stocks[{index}] must be an object")
        code = stock.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"{label}.stocks[{index}].code must be non-empty")
        if code in result:
            raise ValueError(f"{label}.stocks contains duplicate code {code}")
        result[code] = stock
    return result


def validate_runtime_candidate(candidate: dict[str, Any], baseline: dict[str, Any]) -> None:
    if not isinstance(candidate, dict) or not isinstance(baseline, dict):
        raise ValueError("candidate and baseline must be JSON objects")

    candidate_date = _parse_date(candidate.get("generatedAt"), "candidate.generatedAt")
    baseline_date = _parse_date(baseline.get("generatedAt"), "baseline.generatedAt")
    if candidate_date < baseline_date:
        raise ValueError(
            f"candidate.generatedAt regressed from {baseline_date.isoformat()} "
            f"to {candidate_date.isoformat()}"
        )

    candidate_stocks = _stock_map(candidate, "candidate")
    baseline_stocks = _stock_map(baseline, "baseline")

    for code, baseline_stock in baseline_stocks.items():
        candidate_stock = candidate_stocks.get(code)
        if candidate_stock is None:
            raise ValueError(f"candidate is missing baseline instrument {code}")

        baseline_trade_day = _parse_date(
            baseline_stock.get("lastTradeDay"),
            f"baseline.{code}.lastTradeDay",
        )
        candidate_trade_day = _parse_date(
            candidate_stock.get("lastTradeDay"),
            f"candidate.{code}.lastTradeDay",
        )
        if candidate_trade_day < baseline_trade_day:
            raise ValueError(
                f"candidate {code} lastTradeDay regressed from "
                f"{baseline_trade_day.isoformat()} to {candidate_trade_day.isoformat()}"
            )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Dashboard runtime candidate")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()

    validate_runtime_candidate(_load_json(args.candidate), _load_json(args.baseline))
    print("Runtime candidate validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
