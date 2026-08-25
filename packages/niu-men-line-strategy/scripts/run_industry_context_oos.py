"""Run a point-in-time, full-market rolling OOS comparison.

The stock pool is the monthly full A-share universe supplied by the data
platform. Industry membership is joined as-of each bar, and ETF context is
usable only after its 60-observation warmup. Symbols without enough eligible
bars are retained in the coverage report with an explicit skip reason.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from niu_men_line_strategy.backtest import (
    BacktestConfig,
    run_backtest,
    run_buy_and_hold,
)
from niu_men_line_strategy.data import load_tushare_daily_clean
from niu_men_line_strategy.regimes import simple_return_regime
from niu_men_line_strategy.signals import StrategyConfig, build_signals
from niu_men_line_strategy.walk_forward import WalkForwardConfig, walk_forward_folds

_STATE: dict[str, Any] = {}


def _dates(values: pd.Series, *, errors: str = "coerce") -> pd.Series:
    return pd.to_datetime(values.astype("string"), format="%Y%m%d", errors=errors)


def _resolve_research_commit(explicit: str | None) -> str | None:
    if explicit is not None:
        value = explicit.strip()
        return value or None
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _initialise(
    daily_root: str,
    industry_changes: pd.DataFrame,
    universe: pd.DataFrame,
    context: pd.DataFrame,
    backtest_config: BacktestConfig,
    walk_config: WalkForwardConfig,
    min_bars: int,
    simple_trend_lookback: int,
) -> None:
    _STATE.clear()
    _STATE.update(
        {
            "daily_root": daily_root,
            "changes": {
                symbol: group.sort_values("effective_date")
                for symbol, group in industry_changes.groupby("symbol")
            },
            "universe": {
                symbol: group.sort_values("trade_date")
                for symbol, group in universe.groupby("symbol")
            },
            "context": context.set_index(["trade_date", "industry_code"]).sort_index(),
            "backtest_config": backtest_config,
            "walk_config": walk_config,
            "min_bars": min_bars,
            "simple_trend_lookback": simple_trend_lookback,
        }
    )


def _attach_pit_eligibility(data: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    left = pd.DataFrame({"date": data.index})
    selected = pd.merge_asof(
        left,
        snapshots[["trade_date", "selected"]].rename(columns={"trade_date": "snapshot_date"}),
        left_on="date",
        right_on="snapshot_date",
        direction="backward",
        allow_exact_matches=False,
    )["selected"].fillna(0).eq(1)
    return pd.Series(selected.to_numpy(), index=data.index)


def _attach_membership(data: pd.DataFrame, memberships: pd.DataFrame) -> pd.DataFrame:
    left = pd.DataFrame({"date": data.index})
    matched = pd.merge_asof(
        left,
        memberships[["effective_date", "end_date", "mapped_industry_code"]].sort_values("effective_date"),
        left_on="date",
        right_on="effective_date",
        direction="backward",
    )
    active = matched["end_date"].isna() | (matched["date"] <= matched["end_date"])
    result = data.copy()
    result["industry_code"] = matched["mapped_industry_code"].where(active).to_numpy()
    return result


def _join_context(data: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    left = data.reset_index(names="date")
    left["industry_code"] = left["industry_code"].astype("string")
    right = context.reset_index()
    result = left.merge(
        right,
        left_on=["date", "industry_code"],
        right_on=["trade_date", "industry_code"],
        how="left",
    )
    return result.drop(columns=["trade_date"], errors="ignore").set_index("date").sort_index()


def _metrics_row(result: Any) -> dict[str, float]:
    return {key: float(value) if value is not None else float("nan") for key, value in result.metrics.items()}


def _strategy_variants() -> dict[str, StrategyConfig]:
    no_price_volume_filters = {
        "enable_red_three_soldiers": False,
        "enable_long_upper_shadow": False,
    }
    return {
        "nml_baseline": StrategyConfig(),
        "nml_no_price_volume_filters": StrategyConfig(**no_price_volume_filters),
        "simple_20_day_breakout": StrategyConfig(
            nml_atr_multiple=0.0,
            reset_bars=1,
            **no_price_volume_filters,
        ),
        "nml_simple_trend_gate": StrategyConfig(enable_price_regime_gate=True),
        "nml_sector_retreat": StrategyConfig(enable_sector_retreat=True),
    }


def evaluate_symbol(symbol: str) -> dict[str, Any]:
    changes = _STATE["changes"].get(symbol)
    snapshots = _STATE["universe"].get(symbol)
    if changes is None:
        return {"symbol": symbol, "status": "skipped", "skip_reason": "no_industry_history"}
    if snapshots is None:
        return {"symbol": symbol, "status": "skipped", "skip_reason": "not_in_pit_universe"}
    try:
        data = load_tushare_daily_clean(_STATE["daily_root"], symbol, adjusted=True)
    except (FileNotFoundError, ValueError) as exc:
        return {"symbol": symbol, "status": "skipped", "skip_reason": f"data_error:{type(exc).__name__}"}
    data = _attach_membership(data, changes)
    data = data.loc[data["industry_code"].notna()].copy()
    data["pit_eligible"] = _attach_pit_eligibility(data, snapshots)
    data = data.loc[data["pit_eligible"]].copy()
    data = _join_context(data, _STATE["context"])
    data["price_regime"] = simple_return_regime(
        data, lookback=_STATE["simple_trend_lookback"]
    )
    data = data.loc[data["sector_ma60"].notna()].copy()
    if len(data) < _STATE["min_bars"]:
        return {
            "symbol": symbol,
            "status": "skipped",
            "skip_reason": "insufficient_context_ready_bars",
            "context_ready_bars": len(data),
            "industry_codes": "|".join(sorted(data["industry_code"].dropna().unique().tolist())),
        }
    data = data.drop(columns=["pit_eligible"])
    folds = walk_forward_folds(data.index, _STATE["walk_config"])
    if not folds:
        return {"symbol": symbol, "status": "skipped", "skip_reason": "no_walk_forward_fold", "context_ready_bars": len(data)}
    rows: list[dict[str, Any]] = []
    for variant, config in _strategy_variants().items():
        signals = build_signals(data, config)
        for fold_id, fold in enumerate(folds):
            oos = signals.loc[fold.test_start : fold.test_end]
            result = run_backtest(oos, _STATE["backtest_config"])
            row = {
                "symbol": symbol,
                "status": "evaluated",
                "variant": variant,
                "fold_id": fold_id,
                "train_start": fold.train_start.strftime("%Y-%m-%d"),
                "train_end": fold.train_end.strftime("%Y-%m-%d"),
                "test_start": fold.test_start.strftime("%Y-%m-%d"),
                "test_end": fold.test_end.strftime("%Y-%m-%d"),
                "context_ready_bars": len(data),
                "industry_codes": "|".join(sorted(data["industry_code"].dropna().unique().tolist())),
                "entry_signal_count": int(oos["entry_signal"].sum()),
                "sector_retreat_block_count": int(oos["filter_sector_retreat"].sum()),
                "price_regime_block_count": int(oos["filter_price_regime"].sum()),
            }
            row.update(_metrics_row(result))
            rows.append(row)
    for fold_id, fold in enumerate(folds):
        oos = data.loc[fold.test_start : fold.test_end]
        result = run_buy_and_hold(oos, _STATE["backtest_config"])
        row = {
            "symbol": symbol,
            "status": "evaluated",
            "variant": "buy_and_hold",
            "fold_id": fold_id,
            "train_start": fold.train_start.strftime("%Y-%m-%d"),
            "train_end": fold.train_end.strftime("%Y-%m-%d"),
            "test_start": fold.test_start.strftime("%Y-%m-%d"),
            "test_end": fold.test_end.strftime("%Y-%m-%d"),
            "context_ready_bars": len(data),
            "industry_codes": "|".join(sorted(data["industry_code"].dropna().unique().tolist())),
            "entry_signal_count": float("nan"),
            "sector_retreat_block_count": float("nan"),
            "price_regime_block_count": float("nan"),
            "blocked_entry_count": 0.0,
            "blocked_exit_day_count": 0.0,
        }
        row.update(_metrics_row(result))
        rows.append(row)
    return {"symbol": symbol, "status": "evaluated", "rows": rows}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-clean-root", type=Path, required=True)
    parser.add_argument("--industry-changes", type=Path, required=True)
    parser.add_argument("--industry-audit", type=Path, required=True)
    parser.add_argument("--industry-context", type=Path, required=True)
    parser.add_argument("--pit-universe", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--generated-at", default="20260825")
    parser.add_argument("--research-commit")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--min-bars", type=int, default=1008)
    parser.add_argument("--train-bars", type=int, default=756)
    parser.add_argument("--test-bars", type=int, default=252)
    parser.add_argument("--step-bars", type=int, default=252)
    parser.add_argument(
        "--mapping-confidence",
        choices=("expanded", "high"),
        default="expanded",
        help="Use all audited mapped industries or only high-confidence mappings.",
    )
    parser.add_argument(
        "--simple-trend-lookback",
        type=int,
        default=63,
        help="Trailing close-return lookback for the simple price-regime comparator.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    changes = pd.read_parquet(args.industry_changes)
    changes["effective_date"] = _dates(changes["effective_date"], errors="raise")
    changes["end_date"] = _dates(changes["end_date"])
    audit = pd.read_csv(args.industry_audit, dtype="string").fillna("")
    required_audit_columns = {
        "sw_industry_code",
        "mapped_industry_code",
        "status",
        "mapping_confidence",
    }
    missing_audit_columns = sorted(required_audit_columns.difference(audit.columns))
    if missing_audit_columns:
        raise ValueError(
            "industry audit missing required columns: "
            + ", ".join(missing_audit_columns)
        )
    if args.simple_trend_lookback <= 0:
        raise ValueError("simple_trend_lookback must be positive")
    if args.mapping_confidence == "high":
        audit = audit.loc[audit["mapping_confidence"].eq("high")].copy()
    audit_map = audit[
        ["sw_industry_code", "mapped_industry_code", "status", "mapping_confidence"]
    ].rename(columns={"sw_industry_code": "industry_code"})
    changes = changes.merge(audit_map, on="industry_code", how="left")
    changes["mapped_industry_code"] = changes["mapped_industry_code"].where(changes["status"] == "mapped")
    changes = changes.loc[changes["mapped_industry_code"].notna()].copy()
    universe = pd.read_csv(args.pit_universe, dtype={"symbol": "string", "trade_date": "string", "selected": "Int64"})
    universe["trade_date"] = _dates(universe["trade_date"], errors="raise")
    universe = universe.loc[universe["selected"] == 1, ["symbol", "trade_date", "selected"]]
    context = pd.read_parquet(args.industry_context)
    context["trade_date"] = pd.to_datetime(context["trade_date"])
    context = context.loc[context["sector_ma60"].notna()].copy()
    symbols = sorted(set(universe["symbol"]) & set(changes["symbol"]))
    backtest_config = BacktestConfig(commission_bps=5.0, slippage_bps=5.0, lot_size=100.0)
    walk_config = WalkForwardConfig(train_bars=args.train_bars, test_bars=args.test_bars, step_bars=args.step_bars)
    init_args = (
        str(args.daily_clean_root),
        changes,
        universe,
        context,
        backtest_config,
        walk_config,
        args.min_bars,
        args.simple_trend_lookback,
    )
    results: list[dict[str, Any]] = []
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_initialise, initargs=init_args) as pool:
            for index, result in enumerate(pool.map(evaluate_symbol, symbols, chunksize=8), start=1):
                results.append(result)
                if index % 250 == 0:
                    print(f"processed {index}/{len(symbols)}", flush=True)
    else:
        _initialise(*init_args)
        for index, symbol in enumerate(symbols, start=1):
            results.append(evaluate_symbol(symbol))
            if index % 250 == 0:
                print(f"processed {index}/{len(symbols)}", flush=True)

    fold_rows = [row for result in results for row in result.get("rows", [])]
    skip_rows = [{key: value for key, value in result.items() if key != "rows"} for result in results if result.get("status") == "skipped"]
    folds = pd.DataFrame(fold_rows)
    skips = pd.DataFrame(skip_rows)
    stem = f"niu_men_industry_context_oos_full_market_{args.mapping_confidence}_{args.generated_at}"
    folds.to_csv(args.report_dir / f"{stem}.csv", index=False)
    skips.to_csv(args.report_dir / f"{stem}_skips.csv", index=False)
    paired = pd.DataFrame()
    if not folds.empty:
        paired_wide = folds.pivot_table(
            index=["symbol", "fold_id"],
            columns="variant",
            values=["annualized_return", "sharpe", "max_drawdown", "trade_count", "entry_signal_count"],
        )
        available_variants = set(paired_wide.columns.get_level_values(1))
        if "nml_baseline" in available_variants:
            paired_frames = []
            for variant in sorted(available_variants - {"nml_baseline"}):
                frame = pd.DataFrame(index=paired_wide.index)
                frame["comparison_variant"] = variant
                for metric in [
                    "annualized_return",
                    "sharpe",
                    "max_drawdown",
                    "trade_count",
                    "entry_signal_count",
                ]:
                    baseline = paired_wide.get((metric, "nml_baseline"))
                    comparison = paired_wide.get((metric, variant))
                    if baseline is None or comparison is None:
                        continue
                    frame[f"{metric}_baseline"] = baseline
                    frame[f"{metric}_{variant}"] = comparison
                    frame[f"{metric}_delta_{variant}_vs_baseline"] = comparison - baseline
                paired_frames.append(frame.reset_index())
            if paired_frames:
                paired = pd.concat(paired_frames, ignore_index=True)
    paired.to_csv(args.report_dir / f"{stem}_paired.csv", index=False)
    if not folds.empty:
        summary = folds.groupby(["variant", "fold_id"], as_index=False).agg(
            symbols=("symbol", "nunique"),
            annualized_return_median=("annualized_return", "median"),
            sharpe_median=("sharpe", "median"),
            max_drawdown_median=("max_drawdown", "median"),
            trade_count_median=("trade_count", "median"),
            win_rate_median=("win_rate", "median"),
            profit_factor_median=("profit_factor", "median"),
            entry_signal_count=("entry_signal_count", "sum"),
            sector_retreat_block_count=("sector_retreat_block_count", "sum"),
            price_regime_block_count=("price_regime_block_count", "sum"),
        )
        summary.to_csv(args.report_dir / f"{stem}_summary.csv", index=False)
    else:
        summary = pd.DataFrame()
    research_commit = _resolve_research_commit(args.research_commit)
    payload = {
        "schema_version": "niu_men.industry_context_oos_full_market.v2",
        "generated_at": args.generated_at,
        "research_commit": research_commit,
        "stock_pool": str(args.pit_universe),
        "industry_changes": str(args.industry_changes),
        "industry_audit": str(args.industry_audit),
        "industry_context": str(args.industry_context),
        "daily_clean_root": str(args.daily_clean_root),
        "mapping_confidence": args.mapping_confidence,
        "mapped_sw_industry_codes": int(changes["industry_code"].nunique()),
        "mapped_proxy_industry_codes": int(
            changes["mapped_industry_code"].nunique()
        ),
        "simple_trend_lookback": args.simple_trend_lookback,
        "point_in_time_rule": "monthly universe snapshot becomes eligible on the following trading bar",
        "context_ready_rule": "sector_ma60 is non-null",
        "timing": "signals at t close, entries/exits at t+1 open, limit-up/down open fills blocked",
        "backtest_config": asdict(backtest_config),
        "walk_forward_config": asdict(walk_config),
        "min_bars": args.min_bars,
        "variants": list(_strategy_variants()) + ["buy_and_hold"],
        "requested_symbols": len(symbols),
        "evaluated_symbols": int(folds["symbol"].nunique()) if not folds.empty else 0,
        "skipped_symbols": len(skips),
        "fold_rows": len(folds),
        "skip_reasons": {str(k): int(v) for k, v in skips["skip_reason"].value_counts().items()} if not skips.empty else {},
        "aggregate_execution_constraints": {
            str(variant): {
                "blocked_entry_count": int(group["blocked_entry_count"].sum()),
                "blocked_exit_day_count": int(group["blocked_exit_day_count"].sum()),
            }
            for variant, group in folds.groupby("variant")
        } if not folds.empty else {},
        "outputs": {
            "folds": str(args.report_dir / f"{stem}.csv"),
            "summary": str(args.report_dir / f"{stem}_summary.csv"),
            "skips": str(args.report_dir / f"{stem}_skips.csv"),
            "paired": str(args.report_dir / f"{stem}_paired.csv"),
        },
    }
    (args.report_dir / f"{stem}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
