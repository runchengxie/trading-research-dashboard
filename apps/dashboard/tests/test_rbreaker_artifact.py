import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from trading_research.rbreaker_artifact import load_artifact


def _make_artifact(tmp_path: Path, *, path: str = "bars/sz300246.parquet", interval: str = "1m") -> Path:
    root = tmp_path / "artifact"
    bars = root / "bars"
    bars.mkdir(parents=True)
    relative = Path(path)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {
            "datetime": pd.date_range("2026-08-25 09:30", periods=3, freq="min"),
            "open": [10.0, 10.1, 10.2],
            "high": [10.2, 10.3, 10.4],
            "low": [9.9, 10.0, 10.1],
            "close": [10.1, 10.2, 10.3],
            "volume": [1000, 1200, 900],
        }
    )
    frame.to_parquet(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {
        "schemaVersion": "trading_research.rbreaker_input.v1",
        "symbol": "SZ.300246",
        "dataStart": "2026-08-25",
        "dataEnd": "2026-08-25",
        "barInterval": interval,
        "source": "research-runner",
        "generatedAt": "2026-08-26T01:00:00Z",
        "producerCommit": "abc123",
        "previousDay": {"high": 10.5, "low": 9.8, "close": 10.2},
        "files": [{"path": path, "bytes": target.stat().st_size, "sha256": digest}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_load_artifact_accepts_valid_manifest(tmp_path: Path) -> None:
    manifest = load_artifact(_make_artifact(tmp_path))
    assert manifest.symbol == "sz300246"
    assert manifest.bar_interval == "1m"
    assert manifest.previous_day == (10.5, 9.8, 10.2)


def test_load_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="path"):
        load_artifact(_make_artifact(tmp_path, path="../bars/sz300246.parquet"))


def test_load_artifact_rejects_wrong_interval(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="barInterval"):
        load_artifact(_make_artifact(tmp_path, interval="5m"))


def test_load_artifact_rejects_hash_mismatch(tmp_path: Path) -> None:
    root = _make_artifact(tmp_path)
    payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    payload["files"][0]["sha256"] = "0" * 64
    (root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        load_artifact(root)


def test_load_artifact_accepts_us_symbol(tmp_path: Path) -> None:
    root = _make_artifact(tmp_path, path="bars/aapl.us.parquet")
    payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    payload["symbol"] = "AAPL.US"
    (root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    manifest = load_artifact(root)

    assert manifest.symbol == "AAPL.US"
