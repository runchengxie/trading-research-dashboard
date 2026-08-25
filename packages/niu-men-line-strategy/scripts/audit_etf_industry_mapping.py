"""Build and audit the SW2021 L3 to ETF-proxy research inputs.

This script keeps the mapping decision visible in CSV/JSON artifacts. It does
not infer an industry from an ETF name alone. A fund must have a direct named
industry benchmark, an equity/ETF-like fund name, and observed adjusted daily
history before it can become a proxy.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

from niu_men_line_strategy.industry_mapping import (
    PROXY_RULES,
    classify_benchmark,
    classify_sw_industry,
    sw_mapping_confidence,
)


def _dataset_frame(root: Path, columns: list[str]) -> pd.DataFrame:
    files = sorted((root / "data").glob("**/*.parquet"))
    if not files:
        raise FileNotFoundError(f"no parquet partitions under {root / 'data'}")
    table = ds.dataset([str(path) for path in files], format="parquet", partitioning=None).to_table(columns=columns)
    return table.to_pandas()


def _date_column(values: pd.Series, *, errors: str = "coerce") -> pd.Series:
    return pd.to_datetime(values.astype("string"), format="%Y%m%d", errors=errors)


def load_etf_prices(root: Path) -> pd.DataFrame:
    prices = _dataset_frame(root, ["ts_code", "trade_date", "adj_close", "amount"])
    prices["trade_date"] = _date_column(prices["trade_date"], errors="raise")
    prices["adj_close"] = pd.to_numeric(prices["adj_close"], errors="coerce")
    prices["amount"] = pd.to_numeric(prices["amount"], errors="coerce")
    return prices.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)


def build_candidates(fund_basic: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    summary = (
        prices.dropna(subset=["adj_close"])
        .groupby("ts_code", as_index=False)
        .agg(
            first_trade_date=("trade_date", "min"),
            last_trade_date=("trade_date", "max"),
            trade_days=("trade_date", "nunique"),
            median_amount=("amount", "median"),
        )
    )
    fund = fund_basic.copy()
    fund["list_date"] = _date_column(fund["list_date"])
    fund["delist_date"] = _date_column(fund["delist_date"])
    fund = fund.merge(summary, left_on="ts_code", right_on="ts_code", how="inner")
    rows: list[dict[str, object]] = []
    for row in fund.itertuples(index=False):
        if str(row.fund_type) != "股票型":
            continue
        rule = classify_benchmark(row.benchmark, row.name)
        if rule is None:
            continue
        effective = row.list_date if pd.notna(row.list_date) else row.first_trade_date
        rows.append(
            {
                "etf_code": row.ts_code,
                "etf_name": row.name,
                "industry_code": rule.code,
                "industry_name": rule.code,
                "industry_name_cn": rule.name_cn,
                "effective_date": effective.strftime("%Y%m%d"),
                "end_date": row.delist_date.strftime("%Y%m%d") if pd.notna(row.delist_date) else "",
                "mapping_source": "tushare.fund_basic.benchmark",
                "mapping_evidence": row.benchmark,
                "mapping_confidence": "high",
                "mapping_rationale": rule.rationale,
                "first_trade_date": row.first_trade_date.strftime("%Y%m%d"),
                "last_trade_date": row.last_trade_date.strftime("%Y%m%d"),
                "trade_days": int(row.trade_days),
                "median_amount": float(row.median_amount) if pd.notna(row.median_amount) else None,
                "status": row.status,
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("no ETF proxy candidates matched the configured rules")
    return result.sort_values(["industry_code", "first_trade_date", "etf_code"]).reset_index(drop=True)


def build_sw_audit(industry_changes: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    changes = industry_changes.copy()
    changes["effective_date"] = _date_column(changes["effective_date"], errors="raise")
    changes["end_date"] = _date_column(changes["end_date"])
    candidate_counts = candidates.groupby("industry_code").size().to_dict()
    candidate_first = candidates.groupby("industry_code")["first_trade_date"].min().to_dict()
    candidate_last = candidates.groupby("industry_code")["last_trade_date"].max().to_dict()
    rows: list[dict[str, object]] = []
    for (industry_code, industry_name), group in changes.groupby(["industry_code", "industry_name"], dropna=False):
        selected, matches = classify_sw_industry(industry_name)
        confidence = sw_mapping_confidence(industry_name, matches)
        proxy_count = int(candidate_counts.get(selected.code, 0)) if selected else 0
        status = "mapped" if selected and proxy_count else ("no_etf_proxy" if selected else "unmapped")
        rows.append(
            {
                "sw_industry_code": industry_code,
                "sw_industry_name": industry_name,
                "mapped_industry_code": selected.code if selected else "",
                "mapped_industry_name_cn": selected.name_cn if selected else "",
                "mapping_rule": selected.rationale if selected else "",
                "mapping_confidence": confidence if selected else "unmapped",
                "all_matching_proxy_codes": "|".join(matches),
                "candidate_etf_count": proxy_count,
                "proxy_first_trade_date": candidate_first.get(selected.code, "") if selected else "",
                "proxy_last_trade_date": candidate_last.get(selected.code, "") if selected else "",
                "status": status,
                "industry_rows": len(group),
                "industry_symbols": int(group["symbol"].nunique()),
                "industry_first_effective_date": group["effective_date"].min().strftime("%Y%m%d"),
                "industry_last_end_date": group["end_date"].max().strftime("%Y%m%d") if group["end_date"].notna().any() else "",
            }
        )
    audit = pd.DataFrame(rows).sort_values(["status", "sw_industry_code"]).reset_index(drop=True)
    mapped_audit = audit.loc[audit.status == "mapped"]
    name_to_category = mapped_audit.set_index("sw_industry_name")["mapped_industry_code"].to_dict()
    name_to_confidence = mapped_audit.set_index("sw_industry_name")["mapping_confidence"].to_dict()
    changes["mapping_name"] = changes["industry_name"].map(name_to_category)
    changes["mapping_confidence"] = changes["industry_name"].map(name_to_confidence)
    mapped_symbols = set(changes.loc[changes["mapping_name"].notna(), "symbol"])
    high_rows = changes["mapping_confidence"].eq("high")
    high_symbols = set(changes.loc[high_rows, "symbol"])
    medium_rows = changes["mapping_confidence"].eq("medium")
    medium_symbols = set(changes.loc[medium_rows, "symbol"])
    summary = {
        "industry_name_count": int(audit.shape[0]),
        "mapped_industry_name_count": int((audit.status == "mapped").sum()),
        "unmapped_industry_name_count": int((audit.status == "unmapped").sum()),
        "no_etf_proxy_industry_name_count": int((audit.status == "no_etf_proxy").sum()),
        "industry_rows": len(changes),
        "industry_symbols": int(changes["symbol"].nunique()),
        "mapped_industry_rows": int(changes["mapping_name"].notna().sum()),
        "mapped_industry_symbols": int(changes.loc[changes["mapping_name"].notna(), "symbol"].nunique()),
        "row_coverage": float(changes["mapping_name"].notna().mean()),
        "symbol_coverage": float(len(mapped_symbols) / changes["symbol"].nunique()),
        "high_confidence_industry_rows": int(high_rows.sum()),
        "high_confidence_industry_symbols": len(high_symbols),
        "high_confidence_row_coverage": float(high_rows.mean()),
        "high_confidence_symbol_coverage": float(len(high_symbols) / changes["symbol"].nunique()),
        "medium_confidence_industry_rows": int(medium_rows.sum()),
        "medium_confidence_industry_symbols": len(medium_symbols),
        "status_counts": {str(k): int(v) for k, v in audit["status"].value_counts().items()},
        "coverage_by_proxy": {
            str(k): {
                "industry_rows": int(v.shape[0]),
                "industry_symbols": int(v["symbol"].nunique()),
            }
            for k, v in changes.loc[changes["mapping_name"].notna()].groupby("mapping_name")
        },
    }
    return audit, summary


def build_context(prices: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    selected = candidates[["etf_code", "industry_code", "effective_date", "end_date"]].copy()
    selected["effective_date"] = _date_column(selected["effective_date"], errors="raise")
    selected["end_date"] = _date_column(selected["end_date"])
    data = prices.merge(selected, left_on="ts_code", right_on="etf_code", how="inner")
    data = data.loc[
        data["adj_close"].notna()
        & (data["adj_close"] > 0)
        & (data["trade_date"] >= data["effective_date"])
        & (data["end_date"].isna() | (data["trade_date"] <= data["end_date"]))
    ].copy()
    data["etf_return"] = data.groupby("etf_code", sort=False)["adj_close"].pct_change()
    daily = (
        data.dropna(subset=["etf_return"])
        .groupby(["industry_code", "trade_date"], as_index=False)
        .agg(sector_return=("etf_return", "mean"), etf_count=("etf_code", "nunique"))
        .sort_values(["industry_code", "trade_date"])
    )
    daily["sector_close"] = daily.groupby("industry_code", sort=False)["sector_return"].transform(
        lambda values: 100.0 * (1.0 + values.fillna(0.0)).cumprod()
    )
    daily["sector_ma20"] = daily.groupby("industry_code", sort=False)["sector_close"].transform(lambda values: values.rolling(20, min_periods=20).mean())
    daily["sector_ma60"] = daily.groupby("industry_code", sort=False)["sector_close"].transform(lambda values: values.rolling(60, min_periods=60).mean())
    daily["sector_strong"] = ((daily["sector_close"] > daily["sector_ma20"]) & (daily["sector_ma20"] > daily["sector_ma60"])).astype("boolean")
    daily.loc[daily["sector_ma60"].isna(), "sector_strong"] = pd.NA
    return daily[["trade_date", "industry_code", "sector_return", "sector_close", "sector_ma20", "sector_ma60", "sector_strong", "etf_count"]].reset_index(drop=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fund-basic", type=Path, required=True)
    parser.add_argument("--etf-daily-root", type=Path, required=True)
    parser.add_argument("--industry-changes", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--generated-at", default="20260825")
    return parser


def main() -> None:
    args = _parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fund_basic = pd.read_csv(args.fund_basic, dtype="string").fillna("")
    prices = load_etf_prices(args.etf_daily_root)
    candidates = build_candidates(fund_basic, prices)
    candidates_path = args.output_dir / f"etf_industry_mapping_candidates_expanded_{args.generated_at}.csv"
    candidates.to_csv(candidates_path, index=False)
    primary = (
        candidates.assign(_median_amount_numeric=pd.to_numeric(candidates["median_amount"], errors="coerce"))
        .sort_values(["industry_code", "first_trade_date", "trade_days", "_median_amount_numeric"], ascending=[True, True, False, False])
        .groupby("industry_code", as_index=False)
        .head(1)
        .drop(columns=["_median_amount_numeric"])
        .assign(selection_rule="earliest observed eligible proxy, then longest history and median amount")
        .reset_index(drop=True)
    )
    primary.to_csv(args.output_dir / f"etf_industry_mapping_primary_expanded_{args.generated_at}.csv", index=False)

    industry_changes = pd.read_parquet(args.industry_changes)
    audit, coverage = build_sw_audit(industry_changes, candidates)
    audit.to_csv(args.output_dir / f"sw2021_l3_etf_mapping_audit_{args.generated_at}.csv", index=False)

    context = build_context(prices, candidates)
    context_path = args.output_dir / f"industry_etf_context_composite_expanded_{args.generated_at}.parquet"
    context.to_parquet(context_path, index=False)
    context_manifest = {
        "schema_version": "etf.industry_context_composite.expanded.v1",
        "generated_at": args.generated_at,
        "source_mapping": str(candidates_path),
        "source_prices": str(args.etf_daily_root),
        "industries": int(context["industry_code"].nunique()),
        "rows": len(context),
        "trade_dates": int(context["trade_date"].nunique()),
        "industry_codes": sorted(context["industry_code"].unique().tolist()),
        "regime_rule": "sector_close > sector_ma20 and sector_ma20 > sector_ma60",
        "construction": "equal-weight mean of available mapped listed equity-fund daily returns with effective/end-date filtering",
        "signal_timing": "computed at t close, available for t+1 open execution",
        "missing_context_rows": int(context["sector_ma60"].isna().sum()),
        "sector_close_missing_rows": int(context["sector_close"].isna().sum()),
        "context_ready_rows": int(context["sector_ma60"].notna().sum()),
        "output": str(context_path),
    }
    (args.output_dir / f"industry_etf_context_composite_expanded_{args.generated_at}.json").write_text(json.dumps(context_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rules = {
        "schema_version": "etf.industry_mapping_rules.v1",
        "generated_at": args.generated_at,
        "mapping_source": "TuShare fund_basic.benchmark and SW2021 L3 industry_name",
        "benchmark_exclusions": "broad market/style, overseas, bond/cash, and mixed benchmark strings",
        "fund_eligibility": "fund_type=股票型, name contains ETF or LOF, excludes 联接/分级/债/货币/混合, observed adjusted daily history",
        "proxy_rules": [asdict(rule) for rule in PROXY_RULES],
        "coverage": coverage,
        "candidate_count": len(candidates),
        "candidate_industry_count": int(candidates["industry_code"].nunique()),
    }
    (args.output_dir / f"etf_industry_mapping_rules_{args.generated_at}.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(candidates), "context_rows": len(context), "coverage": coverage}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
