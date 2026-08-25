"""Inspectable validation for the local point-in-time research inputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .context import (
    load_industry_changes,
    load_market_context,
    load_point_in_time_universe,
)


@dataclass(frozen=True)
class ValidationReport:
    daily_files: int
    universe_rows: int
    universe_symbols: int
    universe_file_coverage: float
    industry_coverage: float
    market_start: str
    market_end: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_research_inputs(
    *,
    daily_clean_root: str | Path,
    universe_path: str | Path,
    industry_changes_path: str | Path,
    market_index_path: str | Path,
    market_index_code: str = "000906.SH",
) -> ValidationReport:
    """Validate join coverage and temporal coverage before a full-market run."""

    daily_root = Path(daily_clean_root)
    data_dir = daily_root / "data"
    files = {path.stem for path in data_dir.glob("*.parquet")}
    if not files:
        raise ValueError(f"no daily-clean Parquet files found in {data_dir}")
    universe = load_point_in_time_universe(universe_path)
    industry = load_industry_changes(industry_changes_path)
    market = load_market_context(market_index_path, index_code=market_index_code)

    symbols = set(universe["symbol"])
    file_coverage = len(symbols & files) / len(symbols) if symbols else 0.0
    merged = universe[["trade_date", "symbol"]].merge(industry, on="symbol", how="left")
    active = merged[
        (merged["effective_date"] <= merged["trade_date"])
        & (merged["end_date"].isna() | (merged["trade_date"] <= merged["end_date"]))
    ]
    industry_coverage = active[["trade_date", "symbol"]].drop_duplicates().shape[
        0
    ] / len(universe)

    warnings: list[str] = []
    if file_coverage < 1:
        warnings.append("部分点时股票池证券缺少 daily-clean 文件")
    if industry_coverage < 0.99:
        warnings.append("部分点时股票池证券缺少有效行业归属")
    universe_end = universe["trade_date"].max()
    if market.index.max() < universe_end:
        warnings.append("市场上下文早于股票池结束，完整研究应截断到共同结束日")
    return ValidationReport(
        daily_files=len(files),
        universe_rows=len(universe),
        universe_symbols=len(symbols),
        universe_file_coverage=float(file_coverage),
        industry_coverage=float(industry_coverage),
        market_start=str(market.index.min().date()),
        market_end=str(market.index.max().date()),
        warnings=tuple(warnings),
    )
