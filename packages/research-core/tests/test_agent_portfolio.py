from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research_core.agent_portfolio import (
    AGENT_PORTFOLIO_VERSION,
    load_agent_portfolio,
    validate_agent_portfolio,
    validate_target_weights,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "agent_portfolio"


def valid_payload() -> dict:
    return {
        "schemaVersion": AGENT_PORTFOLIO_VERSION,
        "generatedAt": "2026-09-01T22:00:00Z",
        "asOf": "2026-09-01",
        "agent": {
            "id": "glm-daily",
            "provider": "zhipu",
            "model": "glm-4.7-flash",
            "promptVersion": "v1",
            "inputHash": "a" * 64,
        },
        "portfolio": {
            "initialEquity": 100000.0,
            "equity": 100000.0,
            "cash": 100000.0,
            "nav": 1.0,
            "totalReturn": 0.0,
            "maxDrawdown": 0.0,
        },
        "metrics": {"totalReturn": 0.0, "maxDrawdown": 0.0},
        "decision": {
            "targetWeights": {"CASH": 1.0},
            "reasoningSummary": "保持现金，等待下一次观察。",
        },
        "positions": [],
        "trades": [],
        "history": [],
    }


def test_valid_agent_portfolio_is_accepted() -> None:
    validate_agent_portfolio(valid_payload())


def test_agent_portfolio_rejects_wrong_version() -> None:
    payload = valid_payload()
    payload["schemaVersion"] = "trading_research.agent_portfolio.v9"
    with pytest.raises(ValueError, match="agent portfolio schema validation failed"):
        validate_agent_portfolio(payload)


def test_agent_portfolio_rejects_missing_required_field() -> None:
    payload = valid_payload()
    del payload["decision"]
    with pytest.raises(ValueError, match="decision"):
        validate_agent_portfolio(payload)


def test_agent_portfolio_rejects_inconsistent_financial_values() -> None:
    payload = valid_payload()
    payload["portfolio"]["equity"] = 99_000.0
    with pytest.raises(ValueError, match="financial invariants"):
        validate_agent_portfolio(payload)


def test_load_agent_portfolio_reads_and_validates_json(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(valid_payload()), encoding="utf-8")
    assert load_agent_portfolio(path)["schemaVersion"] == AGENT_PORTFOLIO_VERSION


def test_target_weights_normalize_cash_and_accept_small_rounding_error() -> None:
    weights = validate_target_weights(
        {"SPY": 0.8, "CASH": 0.199999},
        {"SPY", "CASH"},
        max_position_weight=0.8,
        min_cash_weight=0.1,
    )
    assert weights["CASH"] == pytest.approx(0.2)


def test_target_weights_preserve_position_cap_when_cash_is_implicit() -> None:
    weights = validate_target_weights(
        {"SPY": 0.8, "CASH": 0.1},
        {"SPY", "CASH"},
        max_position_weight=0.8,
        min_cash_weight=0.1,
    )
    assert weights == {"SPY": 0.8, "CASH": 0.2}


def test_target_weights_reject_unknown_symbol() -> None:
    with pytest.raises(ValueError, match="unknown symbol"):
        validate_target_weights(
            {"NVDA": 0.2, "CASH": 0.8},
            {"SPY", "CASH"},
            max_position_weight=0.8,
            min_cash_weight=0.1,
        )


def test_target_weights_reject_excess_position_weight() -> None:
    with pytest.raises(ValueError, match="maximum position weight"):
        validate_target_weights(
            {"SPY": 0.81, "CASH": 0.19},
            {"SPY", "CASH"},
            max_position_weight=0.8,
            min_cash_weight=0.1,
        )


def test_target_weights_reject_insufficient_cash() -> None:
    with pytest.raises(ValueError, match="minimum cash weight"):
        validate_target_weights(
            {"SPY": 0.95, "CASH": 0.05},
            {"SPY", "CASH"},
            max_position_weight=1.0,
            min_cash_weight=0.1,
        )


def test_target_weights_do_not_mutate_input() -> None:
    source = {"SPY": 0.8, "CASH": 0.2}
    original = copy.deepcopy(source)
    validate_target_weights(source, {"SPY", "CASH"}, 0.8, 0.1)
    assert source == original
