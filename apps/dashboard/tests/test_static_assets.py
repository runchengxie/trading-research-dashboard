from pathlib import Path

import pytest

from scripts.validate_static_assets import validate_snapshots


def test_committed_dashboard_snapshots_are_valid() -> None:
    validate_snapshots()


def test_committed_dashboard_demo_snapshot_includes_tesla() -> None:
    validate_snapshots()

    import json

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
