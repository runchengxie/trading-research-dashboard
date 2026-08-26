import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from test_rbreaker_artifact import _make_artifact

from trading_research.rbreaker_artifact import load_artifact, load_minute_bars


def test_load_minute_bars_maps_columns_and_sorts_index(tmp_path: Path) -> None:
    root = _make_artifact(tmp_path)
    frame = load_minute_bars(load_artifact(root))
    assert frame.index.name == "datetime"
    assert list(frame.columns) == ["开盘", "最高", "最低", "收盘", "成交量"]
    assert frame.index.is_monotonic_increasing


def test_load_minute_bars_rejects_empty_input(tmp_path: Path) -> None:
    root = _make_artifact(tmp_path)
    target = root / "bars/sz300246.parquet"
    pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"]).to_parquet(target)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["bytes"] = target.stat().st_size
    manifest["files"][0]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_minute_bars(load_artifact(root))
