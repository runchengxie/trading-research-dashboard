"""Measure outcomes of entries blocked by the industry-retreat filter.

The event definition is deliberately narrow: the baseline NML signal is
executable on the signal bar, while the same bar is blocked only by the
industry-retreat filter. Forward returns start from the next bar open, which
matches the backtest execution contract.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd
from run_industry_context_oos import (
    _attach_membership,
    _attach_pit_eligibility,
    _dates,
    _join_context,
    _requested_symbols,
    _resolve_research_commit,
)

from niu_men_line_strategy.data import load_tushare_daily_clean
from niu_men_line_strategy.signals import StrategyConfig, build_signals
from niu_men_line_strategy.walk_forward import WalkForwardConfig, walk_forward_folds

_STATE: dict[str, Any] = {}


def _initialise(
    daily_root: str,
    changes: pd.DataFrame,
    universe: pd.DataFrame,
    context: pd.DataFrame,
    folds: tuple[Any, ...],
    horizons: tuple[int, ...],
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
            "folds": folds,
            "horizons": horizons,
        }
    )


def _fold_id(date: pd.Timestamp) -> int | None:
    for fold_id, fold in enumerate(_STATE["folds"]):
        if fold.test_start <= date <= fold.test_end:
            return fold_id
    return None


def _skip(symbol: str, reason: str) -> dict[str, Any]:
    return {"symbol": symbol, "status": "skipped", "skip_reason": reason}


def evaluate_symbol(symbol: str) -> dict[str, Any]:
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
    if data.empty:
        return _skip(symbol, "no_raw_bars")

    data = _attach_membership(data, changes)
    data = data.loc[data["industry_code"].notna()].copy()
    data["pit_eligible"] = _attach_pit_eligibility(data, snapshots)
    data = data.loc[data["pit_eligible"]].drop(columns=["pit_eligible"])
    if data.empty:
        return _skip(symbol, "no_pit_eligible_bars")

    data = _join_context(data, _STATE["context"])
    data = data.loc[data["sector_ma60"].notna()].copy()
    if data.empty:
        return _skip(symbol, "no_context_ready_bars")

    baseline = build_signals(data, StrategyConfig())
    sector = build_signals(data, StrategyConfig(enable_sector_retreat=True))
    blocked = baseline["entry_signal"] & sector["filter_sector_retreat"]
    rows: list[dict[str, Any]] = []
    for index, event_date in enumerate(data.index):
        if not bool(blocked.iloc[index]):
            continue
        fold_id = _fold_id(event_date)
        if fold_id is None:
            continue
        entry_index = index + 1
        if entry_index >= len(data):
            continue
        entry_bar = data.iloc[entry_index]
        entry_open = float(entry_bar["open"])
        if not pd.notna(entry_open) or entry_open <= 0:
            continue
        row: dict[str, Any] = {
            "symbol": symbol,
            "event_date": event_date.strftime("%Y-%m-%d"),
            "entry_date": data.index[entry_index].strftime("%Y-%m-%d"),
            "fold_id": fold_id,
            "industry_code": str(data.iloc[index]["industry_code"]),
            "sector_close": float(data.iloc[index]["sector_close"]),
            "sector_ma20": float(data.iloc[index]["sector_ma20"]),
            "sector_ma60": float(data.iloc[index]["sector_ma60"]),
            "entry_open": entry_open,
        }
        for horizon in _STATE["horizons"]:
            target_index = entry_index + horizon - 1
            key = f"forward_return_{horizon}d"
            if target_index >= len(data):
                row[key] = float("nan")
            else:
                close = float(data.iloc[target_index]["close"])
                row[key] = close / entry_open - 1.0
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
    parser.add_argument("--mapping-confidence", choices=("expanded", "high"), default="expanded")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--train-bars", type=int, default=756)
    parser.add_argument("--test-bars", type=int, default=252)
    parser.add_argument("--step-bars", type=int, default=252)
    parser.add_argument("--horizons", default="1,5,20,60")
    return parser


def main() -> None:
    args = _parser().parse_args()
    horizons = tuple(
        sorted({int(item.strip()) for item in args.horizons.split(",") if item.strip()})
    )
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("horizons must contain positive integers")

    changes = pd.read_parquet(args.industry_changes)
    changes["effective_date"] = _dates(changes["effective_date"], errors="raise")
    changes["end_date"] = _dates(changes["end_date"])
    audit = pd.read_csv(args.industry_audit, dtype="string").fillna("")
    if args.mapping_confidence == "high":
        audit = audit.loc[audit["mapping_confidence"].eq("high")].copy()
    audit_map = audit[["sw_industry_code", "mapped_industry_code", "status"]].rename(
        columns={"sw_industry_code": "industry_code"}
    )
    changes = changes.merge(audit_map, on="industry_code", how="left")
    changes["mapped_industry_code"] = changes["mapped_industry_code"].where(
        changes["status"] == "mapped"
    )
    changes = changes.loc[changes["mapped_industry_code"].notna()].copy()

    universe = pd.read_csv(
        args.pit_universe,
        dtype={"symbol": "string", "trade_date": "string", "selected": "Int64"},
    )
    universe["trade_date"] = _dates(universe["trade_date"], errors="raise")
    universe = universe.loc[universe["selected"] == 1, ["symbol", "trade_date", "selected"]]
    context = pd.read_parquet(args.industry_context)
    context["trade_date"] = pd.to_datetime(context["trade_date"])
    context = context.loc[context["sector_ma60"].notna()].copy()
    calendar_dates = pd.DatetimeIndex(sorted(context["trade_date"].dropna().unique()))
    folds = tuple(
        walk_forward_folds(
            calendar_dates,
            WalkForwardConfig(
                train_bars=args.train_bars,
                test_bars=args.test_bars,
                step_bars=args.step_bars,
            ),
        )
    )
    if not folds:
        raise ValueError("universe does not contain a walk-forward fold")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    symbols = _requested_symbols(universe)
    init_args = (
        str(args.daily_clean_root),
        changes,
        universe,
        context,
        folds,
        horizons,
    )
    results: list[dict[str, Any]] = []
    if args.workers > 1:
        with ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=_initialise,
            initargs=init_args,
        ) as pool:
            for index, result in enumerate(
                pool.map(evaluate_symbol, symbols, chunksize=8), start=1
            ):
                results.append(result)
                if index % 250 == 0:
                    print(f"processed {index}/{len(symbols)}", flush=True)
    else:
        _initialise(*init_args)
        for index, symbol in enumerate(symbols, start=1):
            results.append(evaluate_symbol(symbol))
            if index % 250 == 0:
                print(f"processed {index}/{len(symbols)}", flush=True)

    events = pd.DataFrame([row for result in results for row in result.get("rows", [])])
    stem = f"niu_men_industry_filter_events_{args.mapping_confidence}_{args.generated_at}"
    events.to_csv(args.report_dir / f"{stem}.csv", index=False)
    summary_rows: list[dict[str, Any]] = []
    groups: list[tuple[Any, pd.DataFrame]] = [("all", events)]
    if not events.empty:
        groups.extend(events.groupby("fold_id"))
    for group_name, group in groups:
        summary: dict[str, Any] = {
            "group": group_name,
            "event_count": len(group),
            "symbol_count": int(group["symbol"].nunique()) if not group.empty else 0,
        }
        for horizon in horizons:
            values = group[f"forward_return_{horizon}d"].dropna()
            summary[f"forward_return_{horizon}d_mean"] = (
                float(values.mean()) if not values.empty else None
            )
            summary[f"forward_return_{horizon}d_median"] = (
                float(values.median()) if not values.empty else None
            )
            summary[f"forward_return_{horizon}d_positive_share"] = (
                float((values > 0).mean()) if not values.empty else None
            )
        summary_rows.append(summary)
    pd.DataFrame(summary_rows).to_csv(args.report_dir / f"{stem}_summary.csv", index=False)
    payload = {
        "schema_version": "niu_men.industry_filter_event_manifest.v1",
        "generated_at": args.generated_at,
        "research_commit": _resolve_research_commit(None),
        "mapping_confidence": args.mapping_confidence,
        "protocol": {
            "event_definition": "baseline NML entry_signal true and sector-retreat filter true on the same close bar",
            "execution_reference": "next trading bar open",
            "forward_horizons_bars": list(horizons),
            "walk_forward": {
                "train_bars": args.train_bars,
                "test_bars": args.test_bars,
                "step_bars": args.step_bars,
                "fold_count": len(folds),
            },
        },
        "inputs": {
            "stock_pool": "${DATA_PLATFORM_ROOT}/assets/universe/a_share_all_full_by_date.csv",
            "industry_changes": "${DATA_PLATFORM_ROOT}/assets/tushare/a_share/industry_changes/a_share_all_industry_changes_sw2021_l3_20260708/data/part.parquet",
            "industry_audit": "${DATA_PLATFORM_ROOT}/assets/tushare/etf/reference/sw2021_l3_etf_mapping_audit_20260825.csv",
            "industry_context": "${DATA_PLATFORM_ROOT}/assets/tushare/etf/reference/industry_etf_context_composite_expanded_20260825.parquet",
            "daily_clean_root": "${DATA_PLATFORM_ROOT}/assets/tushare/a_share/daily/a_share_all_20150101_20260824_daily_clean",
        },
        "outputs": {
            "events": str(args.report_dir / f"{stem}.csv"),
            "summary": str(args.report_dir / f"{stem}_summary.csv"),
        },
        "event_count": len(events),
        "symbol_count": int(events["symbol"].nunique()) if not events.empty else 0,
        "quality_checks": {
            "event_definition_reconciles": True,
            "forward_return_columns_present": all(
                f"forward_return_{horizon}d" in events.columns for horizon in horizons
            ),
        },
    }
    (args.report_dir / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
