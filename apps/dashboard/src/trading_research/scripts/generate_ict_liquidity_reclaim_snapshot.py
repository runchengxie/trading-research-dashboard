from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_core.strategy_snapshot import validate_strategy_snapshot

from trading_research.rbreaker_artifact import load_artifact, load_minute_bars
from trading_research.scripts.generate_rbreaker_snapshot import _input_sha256
from trading_research.strategies.ict_liquidity_reclaim import (
    LiquidityReclaimConfig,
    run_liquidity_reclaim,
)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / 2


def _write_json(destination: Path, payload: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def generate_snapshot(
    artifact_root: str | Path,
    output: str | Path,
    *,
    producer_run_id: str,
) -> dict[str, Any]:
    artifact = load_artifact(Path(artifact_root))
    bars = load_minute_bars(artifact)
    if not artifact.symbol.endswith(".US"):
        raise ValueError("ICT liquidity reclaim currently requires a US symbol")
    result = run_liquidity_reclaim(
        bars,
        previous_day_high=artifact.previous_day[0],
        previous_day_low=artifact.previous_day[1],
        config=LiquidityReclaimConfig(),
    )
    trades = result["trades"]
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    net_returns = [float(trade["netReturn"]) for trade in trades]
    gross_returns = [float(trade["grossReturn"]) for trade in trades]
    cost_returns = [float(trade["costReturn"]) for trade in trades]
    mfe_values = [float(trade["mfe"]) for trade in trades]
    mae_values = [float(trade["mae"]) for trade in trades]
    max_drawdown = min(net_returns + [0.0])
    win_rate = sum(value > 0 for value in net_returns) / len(net_returns) if net_returns else None
    profit_factor = None
    losses = sum(value for value in net_returns if value < 0)
    if losses < 0:
        profit_factor = sum(value for value in net_returns if value > 0) / abs(losses)
    metrics = {
        # A single artifact session is intentionally not annualized or used
        # to manufacture a Sharpe ratio; the details retain raw session stats.
        "annualizedReturnMedian": None,
        "sharpeMedian": None,
        "maxDrawdownMedian": max_drawdown,
        "tradeCountMedian": float(len(trades)),
        "winRateMedian": win_rate,
        "profitFactorMedian": profit_factor,
        "entrySignalCount": float(result["entry_signal_count"]),
    }
    snapshot: dict[str, Any] = {
        "schemaVersion": "trading_research.strategy_snapshot.v1",
        "strategy": {
            "id": "ict-liquidity-reclaim",
            "label": "ICT 流动性回收",
            "description": "客观测试前一交易日高低点扫过后收回的日内规则",
        },
        "generatedAt": generated_at,
        "dataDate": artifact.data_end[:10],
        "quality": {
            "status": "warning",
            "checks": {
                "artifactValidated": True,
                "singleSessionResearch": True,
                "annualizedAndSharpeSuppressed": True,
            },
        },
        "provenance": {
            "researchCommit": artifact.producer_commit,
            "dataPlatform": artifact.source,
            "dataPlatformSchemaVersion": "trading_research.rbreaker_input.v1",
            "dataPlatformGeneratedAt": artifact.generated_at,
            "oosSchemaVersion": "trading_research.ict_liquidity_reclaim.v1",
            "oosGeneratedAt": generated_at,
            "artifactRunId": producer_run_id,
            "inputSha256": _input_sha256(artifact.root),
        },
        "coverage": {"requested": 1, "evaluated": 1, "skipped": 0},
        "walkForward": {
            "trainBars": 0,
            "testBars": len(bars),
            "stepBars": len(bars),
            "semantics": "单次历史样本；未将单日结果伪装成滚动 OOS",
            "summaries": [
                {
                    "variant": "ict_liquidity_reclaim_v1",
                    "foldId": 0,
                    "symbols": 1,
                    "startDate": artifact.data_start[:10],
                    "endDate": artifact.data_end[:10],
                    "metrics": metrics,
                }
            ],
        },
        "executionTiming": "signal on bar t close, execution at bar t+1 open; stop-first OHLC tie-break",
        "variants": [
            {
                "id": "ict_liquidity_reclaim_v1",
                "label": "PDH/PDL sweep + reclaim",
                "symbols": 1,
                "foldRows": len(bars),
                "executionCapabilities": {
                    "blockedEntry": "not_applicable",
                    "blockedExitDay": "not_applicable",
                },
                "metrics": metrics,
            }
        ],
        "details": [
            {
                "id": "rule",
                "label": "可执行规则",
                "items": [
                    {
                        "label": "多头",
                        "value": "low < previous-day low 且 close > previous-day low",
                    },
                    {
                        "label": "空头",
                        "value": "high > previous-day high 且 close < previous-day high",
                    },
                    {"label": "入场", "value": "信号后下一根 bar 开盘"},
                    {"label": "风险", "value": "信号 bar 极值外 5bp；目标 1.5R；同 bar 止损优先"},
                    {"label": "成本", "value": "每侧 2bp 滑点；已分别保留 gross/cost/net"},
                ],
            },
            {
                "id": "sample",
                "label": "样本结果",
                "items": [
                    {"label": "标的", "value": artifact.symbol},
                    {"label": "数据区间", "value": f"{artifact.data_start} 至 {artifact.data_end}"},
                    {"label": "交易数", "value": str(len(trades))},
                    {"label": "gross return", "value": f"{sum(gross_returns):.6f}"},
                    {"label": "cost return", "value": f"{sum(cost_returns):.6f}"},
                    {"label": "net return", "value": f"{sum(net_returns):.6f}"},
                    {"label": "MFE median", "value": f"{_median(mfe_values) or 0:.6f}"},
                    {"label": "MAE median", "value": f"{_median(mae_values) or 0:.6f}"},
                    {"label": "研究限制", "value": "单日 artifact；需多日样本后再判断 alpha"},
                ],
            },
        ],
    }
    validate_strategy_snapshot(snapshot)
    _write_json(Path(output), snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an ICT liquidity reclaim snapshot")
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--producer-run-id", required=True)
    args = parser.parse_args()
    generate_snapshot(args.artifact_root, args.output, producer_run_id=args.producer_run_id)


if __name__ == "__main__":
    main()
