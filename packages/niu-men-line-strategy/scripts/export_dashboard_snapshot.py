"""Export a stable dashboard-facing research snapshot from full-market OOS artifacts."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "niu_men.research_snapshot.v2"
EXPECTED_VARIANTS = [
    "nml_baseline",
    "nml_no_price_volume_filters",
    "simple_20_day_breakout",
    "nml_simple_trend_gate",
    "nml_sector_retreat",
    "buy_and_hold",
]
VARIANT_LABELS = {
    "nml_baseline": "NML 基线",
    "nml_no_price_volume_filters": "NML（关闭 OHLCV 过滤）",
    "simple_20_day_breakout": "普通 20 日突破",
    "nml_simple_trend_gate": "NML + 简单趋势 gate",
    "nml_sector_retreat": "NML + 行业退潮过滤",
    "buy_and_hold": "买入持有",
}


def _number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return int(value)
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _iso_date(value: Any) -> str:
    text = str(value)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _snapshot_timestamp(value: str | None) -> str:
    if value is not None:
        text = value.strip()
        if not text:
            raise ValueError("snapshot_generated_at must be non-empty")
        return text
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _asset_name(value: Any) -> str | None:
    if not value:
        return None
    return Path(str(value)).name


def _resolve_artifact(
    oos_json: Path,
    payload: dict[str, Any],
    key: str,
    override: Path | None,
) -> Path:
    if override is not None:
        return override
    raw = payload.get("outputs", {}).get(key)
    if not raw:
        raise ValueError(f"OOS manifest does not define outputs.{key}")
    path = Path(str(raw))
    if not path.is_absolute():
        path = oos_json.parent / path
    return path


def _load_optional_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping_coverage(
    research_manifest: dict[str, Any],
    confidence: str,
) -> dict[str, Any]:
    quality = research_manifest.get("quality", {})
    if confidence == "high":
        return {
            "industryRowCoverage": _number(
                quality.get("expanded_mapping_high_confidence_row_coverage")
            ),
            "symbolCoverage": _number(
                quality.get("expanded_mapping_high_confidence_symbol_coverage")
            ),
        }
    return {
        "industryRowCoverage": _number(
            quality.get("expanded_mapping_industry_row_coverage")
        ),
        "symbolCoverage": _number(
            quality.get("expanded_mapping_symbol_coverage")
        ),
    }


def _variant_aggregates(folds: pd.DataFrame) -> list[dict[str, Any]]:
    metrics = [
        ("annualized_return", "annualizedReturnMedian"),
        ("sharpe", "sharpeMedian"),
        ("max_drawdown", "maxDrawdownMedian"),
        ("trade_count", "tradeCountMedian"),
        ("win_rate", "winRateMedian"),
        ("profit_factor", "profitFactorMedian"),
    ]
    totals = [
        ("entry_signal_count", "entrySignalCount"),
        ("blocked_entry_count", "blockedEntryCount"),
        ("blocked_exit_day_count", "blockedExitDayCount"),
        ("sector_retreat_block_count", "sectorRetreatBlockCount"),
        ("price_regime_block_count", "priceRegimeBlockCount"),
    ]
    result: list[dict[str, Any]] = []
    available = set(folds.get("variant", pd.Series(dtype="string")).dropna().astype(str))
    ordered = list(EXPECTED_VARIANTS)
    ordered.extend(sorted(available.difference(EXPECTED_VARIANTS)))
    for variant in ordered:
        group = folds.loc[folds["variant"].eq(variant)]
        aggregate: dict[str, Any] = {
            "id": variant,
            "label": VARIANT_LABELS.get(variant, variant),
            "symbols": int(group["symbol"].nunique()) if "symbol" in group else 0,
            "foldRows": len(group),
        }
        for source, target in metrics:
            aggregate[target] = (
                _number(pd.to_numeric(group[source], errors="coerce").median())
                if source in group
                else None
            )
        for source, target in totals:
            aggregate[target] = (
                _number(pd.to_numeric(group[source], errors="coerce").sum(min_count=1))
                if source in group
                else None
            )
        result.append(aggregate)
    return result


def _rolling_summaries(summary: pd.DataFrame) -> list[dict[str, Any]]:
    if summary.empty:
        return []
    records: list[dict[str, Any]] = []
    for row in summary.sort_values(["fold_id", "variant"]).to_dict(orient="records"):
        records.append(
            {
                "variant": str(row["variant"]),
                "foldId": int(row["fold_id"]),
                "symbols": int(row["symbols"]),
                "annualizedReturnMedian": _number(row.get("annualized_return_median")),
                "sharpeMedian": _number(row.get("sharpe_median")),
                "maxDrawdownMedian": _number(row.get("max_drawdown_median")),
                "tradeCountMedian": _number(row.get("trade_count_median")),
                "winRateMedian": _number(row.get("win_rate_median")),
                "profitFactorMedian": _number(row.get("profit_factor_median")),
                "entrySignalCount": _number(row.get("entry_signal_count")),
                "sectorRetreatBlockCount": _number(row.get("sector_retreat_block_count")),
                "priceRegimeBlockCount": _number(row.get("price_regime_block_count")),
            }
        )
    return records


def build_snapshot(
    *,
    oos_json: Path,
    folds_csv: Path | None = None,
    summary_csv: Path | None = None,
    skips_csv: Path | None = None,
    research_manifest: Path | None = None,
    snapshot_generated_at: str | None = None,
) -> dict[str, Any]:
    oos = json.loads(oos_json.read_text(encoding="utf-8"))
    folds_path = _resolve_artifact(oos_json, oos, "folds", folds_csv)
    summary_path = _resolve_artifact(oos_json, oos, "summary", summary_csv)
    skips_path = _resolve_artifact(oos_json, oos, "skips", skips_csv)
    folds = pd.read_csv(folds_path)
    summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    skips = pd.read_csv(skips_path) if skips_path.exists() else pd.DataFrame()
    manifest = _load_optional_manifest(research_manifest)

    requested = int(oos.get("requested_symbols", 0))
    evaluated = int(oos.get("evaluated_symbols", 0))
    skipped = int(oos.get("skipped_symbols", len(skips)))
    confidence = str(oos.get("mapping_confidence", "unknown"))
    variants = [str(v) for v in oos.get("variants", [])]
    research_commit = _optional_text(oos.get("research_commit"))
    manifest_schema_version = _optional_text(manifest.get("schema_version"))
    manifest_generated_at = _optional_text(manifest.get("generated_at"))
    manifest_data_date = _optional_text(manifest.get("coverage", {}).get("raw_end"))
    provenance_complete = all(
        value is not None
        for value in (
            research_commit,
            manifest_schema_version,
            manifest_generated_at,
            manifest_data_date,
        )
    )
    duplicate_fold_rows = (
        int(folds.duplicated(["symbol", "variant", "fold_id"]).sum())
        if {"symbol", "variant", "fold_id"}.issubset(folds.columns)
        else None
    )
    checks = {
        "coverageCountsReconcile": requested == evaluated + skipped,
        "expectedVariantsPresent": set(EXPECTED_VARIANTS).issubset(set(variants)),
        "foldKeysUnique": duplicate_fold_rows == 0,
        "oosRowsPresent": not folds.empty,
        "provenanceComplete": provenance_complete,
    }
    quality_status = "pass" if all(checks.values()) else "warning"
    skip_reasons = {
        str(k): int(v)
        for k, v in (oos.get("skip_reasons") or {}).items()
    }
    warmup_skips = int(skip_reasons.get("insufficient_context_ready_bars", 0))

    source_assets = {
        "stockPool": _asset_name(oos.get("stock_pool")),
        "industryChanges": _asset_name(oos.get("industry_changes")),
        "industryAudit": _asset_name(oos.get("industry_audit")),
        "industryContext": _asset_name(oos.get("industry_context")),
        "dailyCleanRoot": _asset_name(oos.get("daily_clean_root")),
        "folds": folds_path.name,
        "summary": summary_path.name,
        "skips": skips_path.name,
    }
    walk = oos.get("walk_forward_config", {})
    snapshot = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _snapshot_timestamp(snapshot_generated_at),
        "source": {
            "researchEngine": "niu-men-line-strategy",
            "researchCommit": research_commit,
            "dataPlatform": "market-data-platform",
            "dataDate": _iso_date(manifest_data_date or oos.get("generated_at", "")),
            "dataPlatformManifest": {
                "schemaVersion": manifest_schema_version,
                "generatedAt": manifest_generated_at,
            },
            "oosSchemaVersion": str(oos.get("schema_version", "")),
            "oosGeneratedAt": _iso_date(oos.get("generated_at", "")),
            "assets": source_assets,
        },
        "mapping": {
            "confidence": confidence,
            "mappedIndustryCodes": int(oos.get("mapped_sw_industry_codes", 0)),
            "mappedProxyIndustryCodes": int(oos.get("mapped_proxy_industry_codes", 0)),
            "coverage": _mapping_coverage(manifest, confidence),
        },
        "coverage": {
            "requestedSymbols": requested,
            "evaluatedSymbols": evaluated,
            "skippedSymbols": skipped,
            "skipReasons": skip_reasons,
            "contextWarmup": {
                "rule": str(oos.get("context_ready_rule", "")),
                "minBars": int(oos.get("min_bars", 0)),
                "skippedSymbols": warmup_skips,
                "contextRows": _number(
                    manifest.get("coverage", {}).get("expanded_context_rows")
                ),
                "readyRows": _number(
                    manifest.get("coverage", {}).get("expanded_context_ready_rows")
                ),
                "warmupRows": _number(
                    manifest.get("coverage", {}).get("expanded_context_warmup_rows")
                ),
            },
        },
        "walkForward": {
            "trainBars": int(walk.get("train_bars", 0)),
            "testBars": int(walk.get("test_bars", 0)),
            "stepBars": int(walk.get("step_bars", 0)),
            "foldSemantics": (
                "foldId is a per-symbol ordinal; calendar dates can differ across symbols"
            ),
            "summaries": _rolling_summaries(summary),
        },
        "variants": _variant_aggregates(folds),
        "executionConstraints": {
            "timing": str(oos.get("timing", "")),
            "byVariant": {
                str(variant): {
                    "blockedEntryCount": int(values.get("blocked_entry_count", 0)),
                    "blockedExitDayCount": int(values.get("blocked_exit_day_count", 0)),
                }
                for variant, values in (
                    oos.get("aggregate_execution_constraints") or {}
                ).items()
            },
        },
        "quality": {
            "status": quality_status,
            "checks": checks,
            "duplicateFoldRows": duplicate_fold_rows,
        },
    }
    return snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oos-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--folds-csv", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--skips-csv", type=Path)
    parser.add_argument("--research-manifest", type=Path)
    parser.add_argument("--snapshot-generated-at")
    return parser


def main() -> None:
    args = _parser().parse_args()
    snapshot = build_snapshot(
        oos_json=args.oos_json,
        folds_csv=args.folds_csv,
        summary_csv=args.summary_csv,
        skips_csv=args.skips_csv,
        research_manifest=args.research_manifest,
        snapshot_generated_at=args.snapshot_generated_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
