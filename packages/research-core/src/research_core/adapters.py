"""Adapters between strategy-specific wire snapshots and the generic envelope.

The generic envelope owns identity, times, quality, provenance, coverage and
typed metric maps so consumers can depend on it instead of strategy fields.
Strategy-specific detail rendering stays with each strategy: Niu Men keeps its
original v2 payload under ``source`` for the registered frontend renderer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

NIU_MEN_WIRE_VERSION = "niu_men.research_snapshot.v2"
_VARIANT_METRIC_KEYS = (
    "annualizedReturnMedian",
    "sharpeMedian",
    "maxDrawdownMedian",
    "tradeCountMedian",
    "winRateMedian",
    "profitFactorMedian",
    "entrySignalCount",
    "blockedEntryCount",
    "blockedExitDayCount",
    "sectorRetreatBlockCount",
    "priceRegimeBlockCount",
)
_SUMMARY_METRIC_KEYS = (
    "annualizedReturnMedian",
    "sharpeMedian",
    "maxDrawdownMedian",
    "tradeCountMedian",
    "winRateMedian",
    "profitFactorMedian",
    "entrySignalCount",
    "sectorRetreatBlockCount",
    "priceRegimeBlockCount",
)


def _metrics(payload: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload[key] for key in keys}


def adapt_niu_men_v2(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Map a ``niu_men.research_snapshot.v2`` document to the generic v1 envelope."""

    source = snapshot["source"]
    manifest = source.get("dataPlatformManifest") or {}
    walk_forward = snapshot["walkForward"]

    summaries = []
    for summary in walk_forward["summaries"]:
        adapted_summary = {
            "variant": summary["variant"],
            "foldId": summary["foldId"],
            "symbols": summary["symbols"],
            "metrics": _metrics(summary, _SUMMARY_METRIC_KEYS),
        }
        if "calendar" in summary:
            adapted_summary["calendar"] = summary["calendar"]
        summaries.append(adapted_summary)

    variants = [
        {
            "id": variant["id"],
            "label": variant["label"],
            "symbols": variant["symbols"],
            "foldRows": variant["foldRows"],
            "executionCapabilities": {
                "blockedEntry": "observed",
                "blockedExitDay": "observed",
            },
            "metrics": _metrics(variant, _VARIANT_METRIC_KEYS),
        }
        for variant in snapshot["variants"]
    ]

    checks: dict[str, bool] = {
        key: value
        for key, value in snapshot["quality"]["checks"].items()
        if isinstance(value, bool)
    }

    return {
        "schemaVersion": "trading_research.strategy_snapshot.v1",
        "strategy": {"id": "niu-men-line", "label": "牛门线"},
        "generatedAt": snapshot["generatedAt"],
        "dataDate": source["dataDate"],
        "quality": {"status": snapshot["quality"]["status"], "checks": checks},
        "provenance": {
            "researchCommit": source.get("researchCommit"),
            "dataPlatform": source["dataPlatform"],
            "dataPlatformSchemaVersion": manifest.get("schemaVersion"),
            "dataPlatformGeneratedAt": manifest.get("generatedAt"),
            "oosSchemaVersion": source["oosSchemaVersion"],
            "oosGeneratedAt": source.get("oosGeneratedAt"),
        },
        "coverage": {
            "requested": snapshot["coverage"]["requestedSymbols"],
            "evaluated": snapshot["coverage"]["evaluatedSymbols"],
            "skipped": snapshot["coverage"]["skippedSymbols"],
        },
        "walkForward": {
            "trainBars": walk_forward["trainBars"],
            "testBars": walk_forward["testBars"],
            "stepBars": walk_forward["stepBars"],
            "semantics": walk_forward["foldSemantics"],
            "summaries": summaries,
        },
        "executionTiming": snapshot["executionConstraints"]["timing"],
        "variants": variants,
        "source": {"wireVersion": NIU_MEN_WIRE_VERSION, "payload": dict(snapshot)},
    }
