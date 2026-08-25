import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

VARIANTS = [
    "nml_baseline",
    "nml_no_price_volume_filters",
    "simple_20_day_breakout",
    "nml_simple_trend_gate",
    "nml_sector_retreat",
    "buy_and_hold",
]


def _write_snapshot_inputs(
    tmp_path: Path,
    *,
    include_provenance: bool = True,
    include_data_date: bool = True,
) -> None:
    folds_rows = []
    summary_rows = []
    for index, variant in enumerate(VARIANTS):
        for symbol in ["000001.SZ", "600000.SH"]:
            folds_rows.append(
                {
                    "symbol": symbol,
                    "variant": variant,
                    "fold_id": 0,
                    "annualized_return": 0.01 + index * 0.001,
                    "sharpe": 0.1 + index * 0.01,
                    "max_drawdown": -0.1,
                    "trade_count": 2,
                    "win_rate": 0.5,
                    "profit_factor": 1.1,
                    "entry_signal_count": 0 if variant == "buy_and_hold" else 3,
                    "blocked_entry_count": 1 if variant == "nml_baseline" else 0,
                    "blocked_exit_day_count": 0,
                    "sector_retreat_block_count": (
                        2 if variant == "nml_sector_retreat" else 0
                    ),
                    "price_regime_block_count": (
                        2 if variant == "nml_simple_trend_gate" else 0
                    ),
                }
            )
        summary_rows.append(
            {
                "variant": variant,
                "fold_id": 0,
                "symbols": 2,
                "annualized_return_median": 0.01 + index * 0.001,
                "sharpe_median": 0.1 + index * 0.01,
                "max_drawdown_median": -0.1,
                "trade_count_median": 2,
                "win_rate_median": 0.5,
                "profit_factor_median": 1.1,
                "entry_signal_count": 0 if variant == "buy_and_hold" else 6,
                "sector_retreat_block_count": (
                    4 if variant == "nml_sector_retreat" else 0
                ),
                "price_regime_block_count": (
                    4 if variant == "nml_simple_trend_gate" else 0
                ),
            }
        )

    pd.DataFrame(folds_rows).to_csv(tmp_path / "folds.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(tmp_path / "summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "000002.SZ",
                "status": "skipped",
                "skip_reason": "insufficient_context_ready_bars",
                "context_ready_bars": 700,
            }
        ]
    ).to_csv(tmp_path / "skips.csv", index=False)

    oos = {
        "schema_version": "niu_men.industry_context_oos_full_market.v2",
        "generated_at": "20260825",
        "stock_pool": "/private/data/a_share_all_full_by_date.csv",
        "industry_changes": "/private/data/sw2021_history.parquet",
        "industry_audit": "/private/data/sw2021_l3_etf_mapping_audit_20260825.csv",
        "industry_context": "/private/data/industry_etf_context_composite_expanded_20260825.parquet",
        "daily_clean_root": "/private/data/a_share_all_20150101_20260824_daily_clean",
        "mapping_confidence": "expanded",
        "mapped_sw_industry_codes": 100,
        "mapped_proxy_industry_codes": 28,
        "context_ready_rule": "sector_ma60 is non-null",
        "timing": "signals at t close, entries/exits at t+1 open, limit-up/down open fills blocked",
        "walk_forward_config": {"train_bars": 756, "test_bars": 252, "step_bars": 252},
        "min_bars": 1008,
        "variants": VARIANTS,
        "requested_symbols": 3,
        "evaluated_symbols": 2,
        "skipped_symbols": 1,
        "skip_reasons": {"insufficient_context_ready_bars": 1},
        "aggregate_execution_constraints": {
            "nml_baseline": {
                "blocked_entry_count": 2,
                "blocked_exit_day_count": 1,
            }
        },
        "outputs": {
            "folds": "folds.csv",
            "summary": "summary.csv",
            "skips": "skips.csv",
            "paired": "paired.csv",
        },
    }
    if include_provenance:
        oos["research_commit"] = "a" * 40
    (tmp_path / "oos.json").write_text(json.dumps(oos), encoding="utf-8")

    coverage = {
        "expanded_context_rows": 46884,
        "expanded_context_ready_rows": 45232,
        "expanded_context_warmup_rows": 1652,
    }
    if include_data_date:
        coverage["raw_end"] = "20260824"
    manifest = {
        "coverage": coverage,
        "quality": {
            "expanded_mapping_industry_row_coverage": 0.8596,
            "expanded_mapping_symbol_coverage": 0.8986,
        },
    }
    if include_provenance:
        manifest["schema_version"] = "niu_men.etf_industry_context_manifest.v1"
        manifest["generated_at"] = "2026-08-25"
    (tmp_path / "research-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _run_export(tmp_path: Path) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "research.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "export_dashboard_snapshot.py"),
            "--oos-json",
            str(tmp_path / "oos.json"),
            "--research-manifest",
            str(tmp_path / "research-manifest.json"),
            "--snapshot-generated-at",
            "2026-08-25T10:15:00Z",
            "--output",
            str(output),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout
    return json.loads(output.read_text(encoding="utf-8"))


def test_export_dashboard_snapshot_builds_stable_contract(tmp_path: Path) -> None:
    _write_snapshot_inputs(tmp_path)

    snapshot = _run_export(tmp_path)

    assert snapshot["schemaVersion"] == "niu_men.research_snapshot.v2"
    assert snapshot["generatedAt"] == "2026-08-25T10:15:00Z"
    source = snapshot["source"]
    assert source["dataDate"] == "2026-08-24"
    assert source["oosGeneratedAt"] == "2026-08-25"
    assert source["researchCommit"] == "a" * 40
    assert source["dataPlatformManifest"] == {
        "schemaVersion": "niu_men.etf_industry_context_manifest.v1",
        "generatedAt": "2026-08-25",
    }
    assert source["assets"]["stockPool"] == "a_share_all_full_by_date.csv"
    assert "/private/data" not in json.dumps(snapshot)
    assert snapshot["coverage"]["requestedSymbols"] == 3
    assert snapshot["coverage"]["contextWarmup"]["skippedSymbols"] == 1
    assert snapshot["mapping"]["coverage"]["symbolCoverage"] == 0.8986
    assert [item["id"] for item in snapshot["variants"]] == VARIANTS
    assert snapshot["variants"][0]["blockedEntryCount"] == 2
    assert snapshot["walkForward"]["summaries"][0]["foldId"] == 0
    assert snapshot["executionConstraints"]["byVariant"]["nml_baseline"] == {
        "blockedEntryCount": 2,
        "blockedExitDayCount": 1,
    }
    assert snapshot["quality"]["checks"]["provenanceComplete"] is True
    assert snapshot["quality"]["status"] == "pass"


def test_export_dashboard_snapshot_marks_missing_provenance(tmp_path: Path) -> None:
    _write_snapshot_inputs(tmp_path, include_provenance=False)

    snapshot = _run_export(tmp_path)

    assert snapshot["source"]["researchCommit"] is None
    assert snapshot["source"]["dataPlatformManifest"] == {
        "schemaVersion": None,
        "generatedAt": None,
    }
    assert snapshot["quality"]["checks"]["provenanceComplete"] is False
    assert snapshot["quality"]["status"] == "warning"


def test_export_dashboard_snapshot_marks_missing_data_date_as_incomplete_provenance(
    tmp_path: Path,
) -> None:
    _write_snapshot_inputs(tmp_path, include_data_date=False)

    snapshot = _run_export(tmp_path)

    assert snapshot["source"]["dataDate"] == "2026-08-25"
    assert snapshot["source"]["researchCommit"] == "a" * 40
    assert snapshot["quality"]["checks"]["provenanceComplete"] is False
    assert snapshot["quality"]["status"] == "warning"


def test_schema_is_valid_json() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (repo_root / "schemas" / "research-snapshot.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["properties"]["schemaVersion"]["const"] == (
        "niu_men.research_snapshot.v2"
    )
    source = schema["properties"]["source"]
    assert "researchCommit" in source["required"]
    assert "oosGeneratedAt" in source["required"]
    assert "dataPlatformManifest" in source["required"]
    assert "provenanceComplete" in schema["properties"]["quality"]["properties"]["checks"]["required"]
