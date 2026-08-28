"""Summarize per-session R-Breaker snapshots into one research report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, TypedDict


class SnapshotRow(TypedDict):
    dataDate: str
    trades: float
    returns: float
    drawdown: float


def summarize_snapshots(paths: list[Path]) -> dict[str, Any]:
    """Aggregate valid generated snapshots without re-running the strategy."""

    rows: list[SnapshotRow] = []
    for path in sorted(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        metrics = payload["variants"][0]["metrics"]
        rows.append(
            {
                "dataDate": payload["dataDate"],
                "trades": float(metrics["tradeCountMedian"] or 0),
                "returns": float(metrics["annualizedReturnMedian"] or 0),
                "drawdown": float(metrics["maxDrawdownMedian"] or 0),
            }
        )
    if not rows:
        raise ValueError("at least one R-Breaker snapshot is required")
    compounded = 1.0
    for row in rows:
        compounded *= 1.0 + float(row["returns"])
    return {
        "days": len(rows),
        "daysWithTrades": sum(1 for row in rows if row["trades"] > 0),
        "totalTrades": int(sum(float(row["trades"]) for row in rows)),
        "compoundedReturn": round(compounded - 1.0, 12),
        "maxDrawdown": max(float(row["drawdown"]) for row in rows),
        "minDrawdown": min(float(row["drawdown"]) for row in rows),
        "sessions": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize_snapshots(args.snapshots)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
