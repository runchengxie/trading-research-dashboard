from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from trading_research.scripts.generate_ict_liquidity_reclaim_snapshot import (
    generate_snapshot,
)
from trading_research.strategies.ict_liquidity_reclaim import (
    LiquidityReclaimConfig,
    evaluate_session,
)


def _bars(rows: list[dict[str, float | str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True)
    return frame.set_index("datetime")


def test_long_reclaim_enters_on_next_bar_and_closes_at_target() -> None:
    bars = _bars(
        [
            {
                "datetime": "2026-08-24T13:30:00Z",
                "open": 100,
                "high": 100.5,
                "low": 99.0,
                "close": 99.8,
            },
            {
                "datetime": "2026-08-24T13:31:00Z",
                "open": 100,
                "high": 100.4,
                "low": 99.8,
                "close": 100.2,
            },
            {
                "datetime": "2026-08-24T13:32:00Z",
                "open": 100.2,
                "high": 101.8,
                "low": 100.0,
                "close": 101.5,
            },
        ]
    )

    trades = evaluate_session(
        bars,
        previous_day_high=105,
        previous_day_low=100,
        config=LiquidityReclaimConfig(stop_buffer_bps=0, target_r=1.5, slippage_bps=0),
    )

    assert len(trades) == 1
    trade = trades[0]
    assert trade["side"] == "long"
    assert trade["signalTime"] == "2026-08-24T09:31:00-04:00"
    assert trade["entryTime"] == "2026-08-24T09:32:00-04:00"
    assert trade["entryPrice"] == 100.2
    assert trade["exitReason"] == "target"
    assert trade["grossReturn"] > 0
    assert trade["netReturn"] == trade["grossReturn"]
    assert trade["mfe"] > 0
    assert trade["mae"] < 0


def test_same_bar_stop_and_target_uses_conservative_stop_first() -> None:
    bars = _bars(
        [
            {
                "datetime": "2026-08-24T13:30:00Z",
                "open": 100,
                "high": 100.5,
                "low": 99.0,
                "close": 100.2,
            },
            {
                "datetime": "2026-08-24T13:31:00Z",
                "open": 100,
                "high": 102,
                "low": 98.5,
                "close": 100.5,
            },
        ]
    )

    trades = evaluate_session(
        bars,
        previous_day_high=105,
        previous_day_low=100,
        config=LiquidityReclaimConfig(stop_buffer_bps=0, target_r=1.5, slippage_bps=0),
    )

    assert trades[0]["exitReason"] == "stop"
    assert trades[0]["netReturn"] < 0


def test_short_reclaim_applies_per_side_cost_and_requires_next_bar() -> None:
    bars = _bars(
        [
            {
                "datetime": "2026-08-24T13:30:00Z",
                "open": 105,
                "high": 106,
                "low": 104.5,
                "close": 105,
            },
            {
                "datetime": "2026-08-24T13:31:00Z",
                "open": 104.8,
                "high": 105.2,
                "low": 103.0,
                "close": 103.5,
            },
            {
                "datetime": "2026-08-24T13:32:00Z",
                "open": 103.5,
                "high": 104,
                "low": 101.5,
                "close": 102,
            },
        ]
    )

    trades = evaluate_session(
        bars,
        previous_day_high=105,
        previous_day_low=95,
        config=LiquidityReclaimConfig(stop_buffer_bps=0, target_r=1.5, slippage_bps=10),
    )

    assert len(trades) == 1
    assert trades[0]["side"] == "short"
    assert trades[0]["costReturn"] < 0
    assert trades[0]["netReturn"] < trades[0]["grossReturn"]


def test_rejects_non_session_date_levels() -> None:
    bars = _bars(
        [
            {"datetime": "2026-08-24T13:30:00Z", "open": 100, "high": 101, "low": 99, "close": 100},
        ]
    )

    trades = evaluate_session(
        bars,
        previous_day_high=105,
        previous_day_low=100,
        config=LiquidityReclaimConfig(),
    )

    assert trades == []


def test_snapshot_preserves_dates_and_marks_single_session_warning(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    (root / "bars").mkdir(parents=True)
    frame = _bars(
        [
            {
                "datetime": "2026-08-24T13:30:00Z",
                "open": 100,
                "high": 100.5,
                "low": 99,
                "close": 99.8,
            },
            {
                "datetime": "2026-08-24T13:31:00Z",
                "open": 100,
                "high": 100.4,
                "low": 99.8,
                "close": 100.2,
            },
            {
                "datetime": "2026-08-24T13:32:00Z",
                "open": 100.2,
                "high": 101.8,
                "low": 100,
                "close": 101.5,
            },
        ]
    ).reset_index(names="datetime")
    frame["volume"] = [1000, 1200, 900]
    target = root / "bars/aapl.us.parquet"
    frame.to_parquet(target)
    manifest = {
        "schemaVersion": "trading_research.rbreaker_input.v1",
        "symbol": "AAPL.US",
        "dataStart": "2026-08-24",
        "dataEnd": "2026-08-24",
        "barInterval": "1m",
        "source": "alpaca",
        "generatedAt": "2026-08-25T01:00:00Z",
        "producerCommit": "abc123",
        "previousDay": {"high": 105, "low": 100, "close": 102},
        "files": [
            {
                "path": "bars/aapl.us.parquet",
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    output = tmp_path / "ict-liquidity-reclaim-research.json"
    snapshot = generate_snapshot(root, output, producer_run_id="run-123")

    assert snapshot["strategy"]["id"] == "ict-liquidity-reclaim"
    assert snapshot["dataDate"] == "2026-08-24"
    assert snapshot["quality"]["status"] == "warning"
    assert snapshot["walkForward"]["summaries"][0]["startDate"] == "2026-08-24"
    assert snapshot["variants"][0]["metrics"]["annualizedReturnMedian"] is None
    assert snapshot["details"][1]["items"][-1]["value"].startswith("单日 artifact")
