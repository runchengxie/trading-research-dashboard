"""Run portfolio-level rolling OOS experiments from point-in-time stock data.

The script first writes a compact per-symbol feature cache, then runs each
calendar fold across all eligible symbols. Raw market data stays in the data
platform. The report directory contains only derived cache partitions and
inspectable portfolio outputs.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
from run_industry_context_oos import (
    _attach_membership,
    _attach_pit_eligibility,
    _dates,
    _join_context,
    _parse_reset_bars_neighborhood,
    _requested_symbols,
    _resolve_research_commit,
)

from niu_men_line_strategy.backtest import BacktestConfig
from niu_men_line_strategy.data import load_tushare_daily_clean
from niu_men_line_strategy.portfolio import (
    PortfolioResult,
    run_equal_weight_buy_and_hold,
    run_portfolio_backtest,
)
from niu_men_line_strategy.regimes import simple_return_regime
from niu_men_line_strategy.signals import StrategyConfig, build_signals
from niu_men_line_strategy.walk_forward import WalkForwardConfig, walk_forward_folds

_STATE: dict[str, Any] = {}


def _portfolio_variants(reset_bars: tuple[int, ...]) -> dict[str, StrategyConfig]:
    no_price_volume = {
        "enable_red_three_soldiers": False,
        "enable_long_upper_shadow": False,
    }
    variants = {
        "nml_baseline": StrategyConfig(),
        "nml_no_price_volume_filters": StrategyConfig(**no_price_volume),
        "simple_20_day_breakout": StrategyConfig(
            nml_atr_multiple=0.0,
            reset_bars=1,
            **no_price_volume,
        ),
        "nml_sector_retreat": StrategyConfig(enable_sector_retreat=True),
        "nml_simple_trend_gate": StrategyConfig(enable_price_regime_gate=True),
        "nml_pullback_formula": StrategyConfig(nml_atr_multiple=-0.5),
        "nml_atr_lag1": StrategyConfig(atr_lag=1),
        "nml_pullback_atr_lag1": StrategyConfig(
            nml_atr_multiple=-0.5,
            atr_lag=1,
        ),
    }
    for value in reset_bars:
        if value == StrategyConfig().reset_bars:
            continue
        variants[f"nml_reset_{value}"] = StrategyConfig(reset_bars=value)
    return variants


def _initialise(
    daily_root: str,
    changes: pd.DataFrame,
    universe: pd.DataFrame,
    context: pd.DataFrame,
    variants: dict[str, StrategyConfig],
    min_bars: int,
    cache_dir: str,
) -> None:
    _STATE.clear()
    _STATE.update(
        {
            "daily_root": daily_root,
            "changes": {
                symbol: group.sort_values("effective_date")
                for symbol, group in changes.groupby("symbol")
            },
            "universe": {
                symbol: group.sort_values("trade_date")
                for symbol, group in universe.groupby("symbol")
            },
            "context": context.set_index(["trade_date", "industry_code"]).sort_index(),
            "variants": variants,
            "min_bars": min_bars,
            "cache_dir": Path(cache_dir),
        }
    )


def _skip(symbol: str, reason: str, **details: Any) -> dict[str, Any]:
    return {"symbol": symbol, "status": "skipped", "skip_reason": reason, **details}


def _prepare_symbol(symbol: str) -> dict[str, Any]:
    changes = _STATE["changes"].get(symbol)
    snapshots = _STATE["universe"].get(symbol)
    if changes is None:
        return _skip(symbol, "no_industry_history")
    if snapshots is None:
        return _skip(symbol, "not_in_pit_universe")
    try:
        data = load_tushare_daily_clean(_STATE["daily_root"], symbol, adjusted=True)
    except (FileNotFoundError, ValueError) as exc:
        return _skip(symbol, f"data_error:{type(exc).__name__}")

    raw_bars = len(data)
    data = _attach_membership(data, changes)
    data = data.loc[data["industry_code"].notna()].copy()
    mapped_industry_bars = len(data)
    if mapped_industry_bars == 0:
        return _skip(symbol, "no_mapped_industry_bars", raw_bars=raw_bars)
    data["pit_eligible"] = _attach_pit_eligibility(data, snapshots)
    data = data.loc[data["pit_eligible"]].drop(columns=["pit_eligible"])
    pit_eligible_bars = len(data)
    if pit_eligible_bars == 0:
        return _skip(
            symbol,
            "no_pit_eligible_bars",
            raw_bars=raw_bars,
            mapped_industry_bars=mapped_industry_bars,
        )
    data = _join_context(data, _STATE["context"])
    data["price_regime"] = simple_return_regime(data, lookback=63)
    data = data.loc[data["sector_ma60"].notna()].copy()
    context_ready_bars = len(data)
    stage_counts = {
        "raw_bars": raw_bars,
        "mapped_industry_bars": mapped_industry_bars,
        "pit_eligible_bars": pit_eligible_bars,
        "context_ready_bars": context_ready_bars,
    }
    if context_ready_bars < _STATE["min_bars"]:
        return _skip(
            symbol,
            "insufficient_context_ready_bars",
            **stage_counts,
        )

    base_columns = ["open", "high", "low", "close", "volume"]
    for column in ("up_limit", "down_limit"):
        if column not in data:
            data[column] = float("nan")
        base_columns.append(column)
    features = data[base_columns].copy()
    for variant, config in _STATE["variants"].items():
        signals = build_signals(data, config)
        if "atr" not in features:
            features["atr"] = signals["atr"]
        features[f"entry__{variant}"] = signals["entry_signal"].astype(bool)
        features[f"exit__{variant}"] = signals["exit_signal"].astype(bool)
    features.reset_index(names="date").to_parquet(
        _STATE["cache_dir"] / f"{_safe_symbol(symbol)}.parquet", index=False
    )
    return {
        "symbol": symbol,
        "status": "evaluated",
        **stage_counts,
        "cache_file": f"{_safe_symbol(symbol)}.parquet",
    }


def _safe_symbol(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", symbol)


def _reuse_cached_symbols(
    symbols: list[str], cache_dir: Path, variants: dict[str, StrategyConfig]
) -> list[dict[str, Any]]:
    """Reuse a previously completed cache after checking its signal columns."""

    cache_files = {path.stem: path for path in cache_dir.glob("*.parquet")}
    required = {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "atr",
        "up_limit",
        "down_limit",
    }
    required.update(
        column
        for variant in variants
        for column in (f"entry__{variant}", f"exit__{variant}")
    )
    prepared: list[dict[str, Any]] = []
    for symbol in symbols:
        path = cache_files.get(_safe_symbol(symbol))
        if path is None:
            prepared.append(_skip(symbol, "cache_missing"))
            continue
        columns = set(pq.ParquetFile(path).schema.names)
        missing = sorted(required.difference(columns))
        if missing:
            raise ValueError(f"cache {path} missing columns: {', '.join(missing)}")
        prepared.append(
            {
                "symbol": symbol,
                "status": "evaluated",
                "cache_file": path.name,
            }
        )
    return prepared


def _load_market_stages(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["trade_date", "market_stage"])
    frame = pd.read_parquet(path)
    required = {"trade_date", "return"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"market benchmark missing columns: {', '.join(missing)}")
    frame = frame.copy()
    frame["trade_date"] = _dates(frame["trade_date"], errors="raise")
    frame = frame.sort_values("trade_date").drop_duplicates("trade_date")
    frame["return_63d"] = frame["return"].rolling(63, min_periods=63).sum()
    frame["volatility_20d"] = frame["return"].rolling(20, min_periods=20).std()
    frame["market_stage"] = "unknown"
    frame.loc[frame["return_63d"] >= 0.05, "market_stage"] = "bull"
    frame.loc[frame["return_63d"] <= -0.05, "market_stage"] = "bear"
    frame.loc[
        frame["return_63d"].between(-0.05, 0.05, inclusive="neither"),
        "market_stage",
    ] = "sideways"
    return frame[["trade_date", "market_stage", "return_63d", "volatility_20d"]]


def _stage_for_fold(stages: pd.DataFrame, test_start: pd.Timestamp) -> str:
    if stages.empty:
        return "unknown"
    eligible = stages.loc[stages["trade_date"] < test_start]
    if eligible.empty:
        return "unknown"
    return str(eligible.iloc[-1]["market_stage"])


def _portfolio_row(
    variant: str,
    fold_id: int,
    fold: Any,
    result: PortfolioResult,
    market_stage: str,
    symbol_count: int,
) -> dict[str, Any]:
    return {
        "variant": variant,
        "fold_id": fold_id,
        "train_start": fold.train_start.strftime("%Y-%m-%d"),
        "train_end": fold.train_end.strftime("%Y-%m-%d"),
        "test_start": fold.test_start.strftime("%Y-%m-%d"),
        "test_end": fold.test_end.strftime("%Y-%m-%d"),
        "market_stage": market_stage,
        "symbol_count": symbol_count,
        **result.metrics,
    }


def _trade_rows(
    result: PortfolioResult,
    variant: str,
    fold_id: int,
    market_stage: str,
) -> list[dict[str, Any]]:
    return [
        {
            "variant": variant,
            "fold_id": fold_id,
            "market_stage": market_stage,
            "symbol": trade.symbol,
            **trade.__dict__,
        }
        for trade in result.trades
    ]


def _read_cache_frame(path: Path) -> tuple[str, pd.DataFrame]:
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"])
    return path.stem, frame.set_index("date").sort_index()


def _load_cache_frames(cache_files: list[Path]) -> dict[str, pd.DataFrame]:
    """Load each cached symbol once so variants reuse the same input bars."""

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(_read_cache_frame, cache_files))


def _load_fold_frames(
    cache_frames: dict[str, pd.DataFrame],
    variant: str,
    fold: Any,
    *,
    require_entry: bool = True,
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    entry_column = f"entry__{variant}"
    exit_column = f"exit__{variant}"
    for symbol, frame in cache_frames.items():
        frame = frame.loc[fold.test_start : fold.test_end]
        if len(frame) < 2:
            continue
        selected = frame[
            [
                "open",
                "high",
                "low",
                "close",
                "atr",
                "up_limit",
                "down_limit",
                entry_column,
                exit_column,
            ]
        ].rename(columns={entry_column: "entry_signal", exit_column: "exit_signal"})
        if require_entry and not selected["entry_signal"].any():
            continue
        frames[symbol] = selected
    return frames


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-clean-root", type=Path, required=True)
    parser.add_argument("--industry-changes", type=Path, required=True)
    parser.add_argument("--industry-audit", type=Path, required=True)
    parser.add_argument("--industry-context", type=Path, required=True)
    parser.add_argument("--pit-universe", type=Path, required=True)
    parser.add_argument("--market-benchmark", type=Path)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--generated-at", default="20260826")
    parser.add_argument("--research-commit")
    parser.add_argument("--mapping-confidence", choices=("expanded", "high"), default="expanded")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reuse-cache", action="store_true")
    parser.add_argument("--min-bars", type=int, default=1008)
    parser.add_argument("--train-bars", type=int, default=756)
    parser.add_argument("--test-bars", type=int, default=252)
    parser.add_argument("--step-bars", type=int, default=252)
    parser.add_argument("--reset-bars-neighborhood", default="1,3,5,10,20")
    parser.add_argument(
        "--variants",
        help="comma-separated strategy variants to run, default is the full matrix",
    )
    parser.add_argument("--commission-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--lot-size", type=float, default=100.0)
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.cache_dir or args.report_dir / "feature_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    research_commit = _resolve_research_commit(args.research_commit)
    reset_values = _parse_reset_bars_neighborhood(args.reset_bars_neighborhood)
    variants = _portfolio_variants(reset_values)
    if args.variants:
        requested_variants = tuple(
            value.strip() for value in args.variants.split(",") if value.strip()
        )
        unknown = sorted(set(requested_variants).difference(variants))
        if unknown:
            raise ValueError(f"unknown portfolio variants: {', '.join(unknown)}")
        variants = {name: variants[name] for name in requested_variants}

    changes = pd.read_parquet(args.industry_changes)
    changes["effective_date"] = _dates(changes["effective_date"], errors="raise")
    changes["end_date"] = _dates(changes["end_date"])
    audit = pd.read_csv(args.industry_audit, dtype="string").fillna("")
    if args.mapping_confidence == "high":
        audit = audit.loc[audit["mapping_confidence"].eq("high")].copy()
    audit_map = audit[
        ["sw_industry_code", "mapped_industry_code", "status"]
    ].rename(columns={"sw_industry_code": "industry_code"})
    changes = changes.merge(audit_map, on="industry_code", how="left")
    changes["mapped_industry_code"] = changes["mapped_industry_code"].where(
        changes["status"].eq("mapped")
    )
    changes = changes.loc[changes["mapped_industry_code"].notna()].copy()
    universe = pd.read_csv(
        args.pit_universe,
        dtype={"symbol": "string", "trade_date": "string", "selected": "Int64"},
    )
    universe["trade_date"] = _dates(universe["trade_date"], errors="raise")
    universe = universe.loc[universe["selected"].eq(1), ["symbol", "trade_date", "selected"]]
    context = pd.read_parquet(args.industry_context)
    context["trade_date"] = pd.to_datetime(context["trade_date"])
    context = context.loc[context["sector_ma60"].notna()].copy()
    symbols = _requested_symbols(universe)
    backtest_config = BacktestConfig(
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        lot_size=args.lot_size,
    )
    walk_config = WalkForwardConfig(
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        step_bars=args.step_bars,
    )
    calendar_dates = pd.DatetimeIndex(sorted(context["trade_date"].unique()))
    folds = walk_forward_folds(calendar_dates, walk_config)
    if not folds:
        raise ValueError("context calendar does not contain a walk-forward fold")

    if args.reuse_cache:
        prepared = _reuse_cached_symbols(symbols, cache_dir, variants)
    else:
        init_args = (
            str(args.daily_clean_root),
            changes,
            universe,
            context,
            variants,
            args.min_bars,
            str(cache_dir),
        )
        prepared = []
        if args.workers > 1:
            with ProcessPoolExecutor(
                max_workers=args.workers,
                initializer=_initialise,
                initargs=init_args,
            ) as pool:
                for index, result in enumerate(
                    pool.map(_prepare_symbol, symbols, chunksize=8), start=1
                ):
                    prepared.append(result)
                    if index % 250 == 0:
                        print(f"prepared {index}/{len(symbols)}", flush=True)
        else:
            _initialise(*init_args)
            for index, symbol in enumerate(symbols, start=1):
                prepared.append(_prepare_symbol(symbol))
                if index % 250 == 0:
                    print(f"prepared {index}/{len(symbols)}", flush=True)

    evaluated = [row for row in prepared if row["status"] == "evaluated"]
    skipped = [row for row in prepared if row["status"] == "skipped"]
    cache_files = sorted(cache_dir.glob("*.parquet"))
    market_stages = _load_market_stages(args.market_benchmark)
    cache_frames = _load_cache_frames(cache_files)
    fold_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    for fold_id, fold in enumerate(folds):
        market_stage = _stage_for_fold(market_stages, fold.test_start)
        base_frames = _load_fold_frames(
            cache_frames, "nml_baseline", fold, require_entry=False
        )
        if base_frames:
            result = run_equal_weight_buy_and_hold(base_frames, backtest_config)
            fold_rows.append(
                _portfolio_row(
                    "buy_and_hold", fold_id, fold, result, market_stage, len(base_frames)
                )
            )
            trade_rows.extend(_trade_rows(result, "buy_and_hold", fold_id, market_stage))
            for _, row in result.equity_curve.reset_index(names="date").iterrows():
                equity_rows.append(
                    {
                        "variant": "buy_and_hold",
                        "fold_id": fold_id,
                        "market_stage": market_stage,
                        "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                        **row.drop(labels="date").to_dict(),
                    }
                )
        for variant in variants:
            frames = _load_fold_frames(cache_frames, variant, fold)
            if not frames:
                continue
            result = run_portfolio_backtest(frames, backtest_config)
            fold_rows.append(
                _portfolio_row(variant, fold_id, fold, result, market_stage, len(frames))
            )
            trade_rows.extend(_trade_rows(result, variant, fold_id, market_stage))
            for _, row in result.equity_curve.reset_index(names="date").iterrows():
                equity_rows.append(
                    {
                        "variant": variant,
                        "fold_id": fold_id,
                        "market_stage": market_stage,
                        "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                        **row.drop(labels="date").to_dict(),
                    }
                )

    stem = f"niu_men_portfolio_oos_{args.mapping_confidence}_{args.generated_at}"
    folds_frame = pd.DataFrame(fold_rows)
    trades_frame = pd.DataFrame(trade_rows)
    equity_frame = pd.DataFrame(equity_rows)
    skips_frame = pd.DataFrame(skipped)
    prepared_frame = pd.DataFrame(prepared)
    folds_frame.to_csv(args.report_dir / f"{stem}_folds.csv", index=False)
    trades_frame.to_csv(args.report_dir / f"{stem}_trades.csv", index=False)
    equity_frame.to_csv(args.report_dir / f"{stem}_equity.csv", index=False)
    skips_frame.to_csv(args.report_dir / f"{stem}_skips.csv", index=False)
    prepared_frame.to_csv(args.report_dir / f"{stem}_coverage.csv", index=False)
    summary = (
        folds_frame.groupby(["variant", "market_stage"], as_index=False)
        .agg(
            folds=("fold_id", "nunique"),
            symbols_median=("symbol_count", "median"),
            annualized_return_median=("annualized_return", "median"),
            sharpe_median=("sharpe", "median"),
            max_drawdown_median=("max_drawdown", "median"),
            trade_count_median=("trade_count", "median"),
            turnover_median=("turnover", "median"),
        )
        if not folds_frame.empty
        else pd.DataFrame()
    )
    summary.to_csv(args.report_dir / f"{stem}_summary.csv", index=False)
    payload = {
        "schema_version": "niu_men.portfolio_oos.v1",
        "generated_at": args.generated_at,
        "research_commit": research_commit,
        "mapping_confidence": args.mapping_confidence,
        "data_date": context["trade_date"].max().strftime("%Y-%m-%d"),
        "stock_pool": str(args.pit_universe),
        "inputs": {
            "daily_clean_root": str(args.daily_clean_root),
            "industry_changes": str(args.industry_changes),
            "industry_audit": str(args.industry_audit),
            "industry_context": str(args.industry_context),
            "market_benchmark": str(args.market_benchmark) if args.market_benchmark else None,
        },
        "protocol": {
            "execution": "signals at t close, per-symbol next-bar open execution, shared cash and per-symbol risk caps",
            "walk_forward": asdict(walk_config),
            "context_ready_rule": "sector_ma60 is non-null",
            "market_stage_rule": "CSI 300 trailing 63-day return: bull >= 5%, bear <= -5%, otherwise sideways, using data before test start",
            "backtest_config": asdict(backtest_config),
            "cache_reused": args.reuse_cache,
        },
        "variants": {
            name: asdict(config) for name, config in variants.items()
        },
        "coverage": {
            "requested_symbols": len(symbols),
            "evaluated_symbols": len(evaluated),
            "skipped_symbols": len(skipped),
            "coverage": len(evaluated) / len(symbols) if symbols else 0.0,
            "skip_reasons": {
                str(key): int(value)
                for key, value in skips_frame["skip_reason"].value_counts().items()
            }
            if not skips_frame.empty
            else {},
        },
        "quality_checks": {
            "fold_rows_present": not folds_frame.empty,
            "trade_keys_unique": not trades_frame.duplicated(
                ["variant", "fold_id", "symbol", "entry_time", "exit_time"]
            ).any()
            if not trades_frame.empty
            else True,
            "equity_keys_unique": not equity_frame.duplicated(
                ["variant", "fold_id", "date"]
            ).any()
            if not equity_frame.empty
            else True,
            "max_drawdown_non_positive": bool(
                (folds_frame["max_drawdown"] <= 0).all()
            )
            if not folds_frame.empty
            else True,
            "provenance_complete": research_commit is not None,
        },
        "outputs": {
            "folds": str(args.report_dir / f"{stem}_folds.csv"),
            "trades": str(args.report_dir / f"{stem}_trades.csv"),
            "equity": str(args.report_dir / f"{stem}_equity.csv"),
            "summary": str(args.report_dir / f"{stem}_summary.csv"),
            "coverage": str(args.report_dir / f"{stem}_coverage.csv"),
            "skips": str(args.report_dir / f"{stem}_skips.csv"),
        },
    }
    (args.report_dir / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
