from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from research_core.strategy_snapshot import validate_strategy_snapshot

from trading_research.rbreaker_artifact import load_artifact, load_minute_bars
from trading_research.strategies.rbreaker import CustomPandasData, run_strategy


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _input_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _metric(value: Any) -> float | None:
    return None if value is None else float(value)


def generate_snapshot(
    artifact_root: str | Path,
    output: str | Path,
    *,
    producer_run_id: str,
) -> dict[str, Any]:
    artifact = load_artifact(Path(artifact_root))
    bars = load_minute_bars(artifact)
    if CustomPandasData is None:
        raise RuntimeError("backtrader is required to generate an R-Breaker snapshot")

    params = SimpleNamespace(f1=0.35, f2=0.07, f3=0.25, reverse=2.0, rangemin=0.5)
    result = run_strategy(
        CustomPandasData(dataname=bars),
        params,
        artifact.previous_day,
        plot=False,
        save_trades=False,
    )
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    snapshot: dict[str, Any] = {
        "schemaVersion": "trading_research.strategy_snapshot.v1",
        "strategy": {
            "id": "r-breaker",
            "label": "R-Breaker",
            "description": "日内突破与反转策略研究",
        },
        "generatedAt": generated_at,
        "dataDate": artifact.data_end,
        "quality": {"status": "pass", "checks": {"artifactValidated": True}},
        "provenance": {
            "researchCommit": artifact.producer_commit,
            "dataPlatform": artifact.source,
            "dataPlatformSchemaVersion": "trading_research.rbreaker_input.v1",
            "dataPlatformGeneratedAt": artifact.generated_at,
            "oosSchemaVersion": "trading_research.rbreaker_backtest_summary.v1",
            "oosGeneratedAt": generated_at,
            "artifactRunId": producer_run_id,
            "inputSha256": _input_sha256(artifact.root),
            "backtraderVersion": _package_version("backtrader"),
        },
        "coverage": {"requested": 1, "evaluated": 1, "skipped": 0},
        "walkForward": None,
        "executionTiming": "signal on bar t close, execution at bar t+1 open",
        "variants": [
            {
                "id": "rb_default",
                "label": "R-Breaker 默认参数",
                "symbols": 1,
                "foldRows": len(bars),
                "metrics": {
                    "annualizedReturnMedian": _metric(result["returns"]),
                    "sharpeMedian": _metric(result["sharpe"]),
                    "maxDrawdownMedian": _metric(result["drawdown"]),
                    "tradeCountMedian": _metric(result["trade_count"]),
                    "winRateMedian": _metric(result["accuracy"] / 100),
                    "profitFactorMedian": None,
                },
            }
        ],
        "details": [
            {
                "id": "execution",
                "label": "执行约束",
                "items": [
                    {"label": "标的", "value": artifact.symbol},
                    {"label": "数据区间", "value": f"{artifact.data_start} 至 {artifact.data_end}"},
                ],
            }
        ],
    }
    validate_strategy_snapshot(snapshot)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, prefix=f".{destination.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an R-Breaker research snapshot")
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--producer-run-id", required=True)
    args = parser.parse_args()
    generate_snapshot(args.artifact_root, args.output, producer_run_id=args.producer_run_id)


if __name__ == "__main__":
    main()
