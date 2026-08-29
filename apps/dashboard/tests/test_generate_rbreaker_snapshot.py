import json
from pathlib import Path

from test_rbreaker_artifact import _make_artifact

import trading_research.scripts.generate_rbreaker_snapshot as snapshot_module
from trading_research.scripts.generate_rbreaker_snapshot import generate_snapshot


def test_generator_writes_generic_snapshot_with_run_provenance(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path / "input")
    output = tmp_path / "web/public/rbreaker-research.json"

    snapshot = generate_snapshot(artifact, output, producer_run_id="run-123")

    assert snapshot["schemaVersion"] == "trading_research.strategy_snapshot.v1"
    assert snapshot["strategy"]["id"] == "r-breaker"
    assert snapshot["dataDate"] == "2026-08-25"
    assert snapshot["provenance"]["artifactRunId"] == "run-123"
    assert snapshot["walkForward"]["summaries"][0]["startDate"] == "2026-08-25"
    assert snapshot["walkForward"]["summaries"][0]["endDate"] == "2026-08-25"
    assert snapshot["variants"][0]["metrics"]["maxDrawdownMedian"] <= 0
    assert json.loads(output.read_text(encoding="utf-8")) == snapshot


def test_generator_converts_backtrader_drawdown_percent_to_ratio(
    tmp_path: Path, monkeypatch
) -> None:
    artifact = _make_artifact(tmp_path / "input")
    output = tmp_path / "rbreaker-research.json"

    monkeypatch.setattr(
        snapshot_module,
        "run_strategy",
        lambda *args, **kwargs: {
            "returns": -0.0537,
            "sharpe": None,
            "drawdown": 11.5868,
            "accuracy": 50.0,
            "trade_count": 24,
        },
    )

    snapshot = generate_snapshot(artifact, output, producer_run_id="run-123")

    assert snapshot["variants"][0]["metrics"]["maxDrawdownMedian"] == 0.115868


def test_generator_preserves_existing_snapshot_on_failure(tmp_path: Path) -> None:
    output = tmp_path / "rbreaker-research.json"
    output.write_text('{"old": true}\n', encoding="utf-8")

    try:
        generate_snapshot(tmp_path / "missing-artifact", output, producer_run_id="run-123")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid artifact should fail")

    assert output.read_text(encoding="utf-8") == '{"old": true}\n'
