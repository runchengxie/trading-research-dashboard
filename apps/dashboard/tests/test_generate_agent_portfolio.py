from __future__ import annotations

import json
from pathlib import Path

import pytest
from research_core.agent_portfolio import load_agent_portfolio

from trading_research.scripts.generate_agent_portfolio import generate_snapshot

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "agent_portfolio"


def _write_inputs(tmp_path: Path, model_response: str | None = None) -> tuple[Path, Path, Path]:
    previous = {
        "schemaVersion": "trading_research.agent_portfolio.v1",
        "generatedAt": "2026-08-31T22:00:00Z",
        "asOf": "2026-08-31",
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
        "decision": {"targetWeights": {"CASH": 1.0}, "reasoningSummary": "观望。"},
        "positions": [],
        "trades": [],
        "history": [{"asOf": "2026-08-31", "equity": 100000.0, "nav": 1.0, "drawdown": 0.0}],
    }
    prices_path = tmp_path / "prices.json"
    previous_path = tmp_path / "previous.json"
    response_path = tmp_path / "model-response.json"
    prices_path.write_text(json.dumps({"SPY": 100.0}, ensure_ascii=False), encoding="utf-8")
    previous_path.write_text(json.dumps(previous, ensure_ascii=False), encoding="utf-8")
    response_path.write_text(model_response or json.dumps({
        "target_weights": {"SPY": 0.5, "CASH": 0.5},
        "reasoning_summary": "趋势稳定，保持适度仓位。",
    }, ensure_ascii=False), encoding="utf-8")
    return prices_path, previous_path, response_path


def test_generator_builds_valid_latest_snapshot(tmp_path: Path) -> None:
    prices, previous, response = _write_inputs(tmp_path)
    output = tmp_path / "latest.json"
    payload = generate_snapshot(
        prices_path=prices,
        previous_path=previous,
        model_response_path=response,
        output=output,
        as_of="2026-09-01",
        generated_at="2026-09-01T22:00:00Z",
    )
    assert load_agent_portfolio(output) == payload
    assert payload["portfolio"]["nav"] == pytest.approx(0.9995)
    assert payload["agent"]["provider"] == "zhipu"
    assert payload["decision"]["targetWeights"] == {"SPY": 0.5, "CASH": 0.5}


def test_generator_does_not_replace_output_when_validation_fails(tmp_path: Path) -> None:
    prices, previous, response = _write_inputs(tmp_path, "not json")
    output = tmp_path / "latest.json"
    original = '{"reviewed": true}\n'
    output.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="model response"):
        generate_snapshot(
            prices_path=prices,
            previous_path=previous,
            model_response_path=response,
            output=output,
            as_of="2026-09-01",
            generated_at="2026-09-01T22:00:00Z",
        )
    assert output.read_text(encoding="utf-8") == original


def test_generator_only_allows_symbols_with_prices(tmp_path: Path) -> None:
    prices, previous, response = _write_inputs(
        tmp_path,
        json.dumps(
            {
                "target_weights": {"QQQ": 0.5, "CASH": 0.5},
                "reasoning_summary": "测试不可交易标的。",
            },
            ensure_ascii=False,
        ),
    )
    output = tmp_path / "latest.json"

    with pytest.raises(ValueError, match="unknown symbol"):
        generate_snapshot(
            prices_path=prices,
            previous_path=previous,
            model_response_path=response,
            output=output,
            as_of="2026-09-01",
            generated_at="2026-09-01T22:00:00Z",
        )


def test_generator_scales_risky_weights_to_keep_the_minimum_cash(tmp_path: Path) -> None:
    prices, previous, response = _write_inputs(
        tmp_path,
        json.dumps(
            {
                "target_weights": {"SPY": 0.8, "QQQ": 0.15, "CASH": 0.05},
                "reasoning_summary": "测试最低现金约束。",
            },
            ensure_ascii=False,
        ),
    )
    prices_payload = json.loads(prices.read_text(encoding="utf-8"))
    prices_payload["QQQ"] = 200.0
    prices.write_text(json.dumps(prices_payload), encoding="utf-8")
    output = tmp_path / "latest.json"

    payload = generate_snapshot(
        prices_path=prices,
        previous_path=previous,
        model_response_path=response,
        output=output,
        as_of="2026-09-01",
        generated_at="2026-09-01T22:00:00Z",
    )

    assert payload["decision"]["targetWeights"]["CASH"] == pytest.approx(0.1)
    assert payload["decision"]["targetWeights"]["SPY"] == pytest.approx(0.8 * 0.9 / 0.95)
    assert payload["decision"]["targetWeights"]["QQQ"] == pytest.approx(0.15 * 0.9 / 0.95)
