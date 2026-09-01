import json
from pathlib import Path

import pytest

from scripts.validate_static_assets import validate_snapshots


def test_committed_dashboard_snapshots_are_valid() -> None:
    validate_snapshots()


def test_committed_agent_portfolio_snapshot_is_valid() -> None:
    validate_snapshots()


def test_static_validation_rejects_invalid_agent_portfolio(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_text(
        (Path(__file__).parents[1] / "web/public/data.json").read_text(), encoding="utf-8"
    )
    agent_path = tmp_path / "agent.json"
    agent_path.write_text('{"schemaVersion":"invalid"}', encoding="utf-8")

    with pytest.raises(ValueError, match="agent portfolio schema validation failed"):
        validate_snapshots(data_path, tmp_path / "research.json", agent_path=agent_path)


def test_committed_dashboard_demo_snapshot_includes_tesla() -> None:
    validate_snapshots()

    payload = json.loads((Path(__file__).parents[1] / "web/public/data.json").read_text())
    tesla = next(stock for stock in payload["stocks"] if stock["code"] == "TSLA.US")

    assert tesla["market"] == "US"
    assert tesla["currency"] == "USD"
    assert tesla["daily"]
    assert tesla["intraday"]


def test_empty_data_snapshot_is_rejected(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_text(
        '{"generatedAt":"2026-08-26","stocks":[]}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="at least one instrument"):
        validate_snapshots(data_path, tmp_path / "research.json")


def test_missing_data_snapshot_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="is missing"):
        validate_snapshots(tmp_path / "data.json", tmp_path / "research.json")


def test_authoritative_validation_requires_contextual_research(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_text(
        '{"generatedAt":"2026-08-28","stocks":[{"code":"TEST.US"}]}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="contextualResearch is required"):
        validate_snapshots(data_path, tmp_path / "research.json", require_contextual=True)


def test_authoritative_validation_accepts_positive_contextual_coverage(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    payload = json.loads((Path(__file__).parents[1] / "web/public/data.json").read_text())
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    validate_snapshots(data_path, tmp_path / "research.json", require_contextual=True)


def test_static_validation_rejects_malformed_nested_contextual_payload(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_text(
        json.dumps(
            {
                "generatedAt": "2026-08-30",
                "stocks": [{"code": "TEST.US"}],
                "contextualResearch": {
                    "schemaVersion": "trading_research.contextual_snapshot.v1",
                    "generatedAt": "2026-08-30",
                    "dataDate": "2026-08-30",
                    "quality": {"status": "pass", "warnings": []},
                    "coverage": {"requested": 1, "evaluated": 1, "skipped": 0},
                    "contexts": [{}],
                    "setupEvents": [],
                    "eventStudies": [],
                    "provenance": {"source": "test", "definitionVersion": "v1"},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "research.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="instrument"):
        validate_snapshots(data_path, tmp_path / "research.json")
