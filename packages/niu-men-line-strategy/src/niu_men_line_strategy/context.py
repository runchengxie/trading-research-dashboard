"""Point-in-time universe and market-context helpers for research runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _as_trade_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values.astype("string"), format="%Y%m%d", errors="raise")


def load_point_in_time_universe(path: str | Path) -> pd.DataFrame:
    """Load the monthly point-in-time universe snapshots supplied by the platform."""

    data = pd.read_csv(path, dtype={"symbol": "string", "trade_date": "string"})
    required = {"trade_date", "symbol", "liq_metric", "selected"}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"universe is missing columns: {', '.join(missing)}")
    data = data.copy()
    data["trade_date"] = _as_trade_dates(data["trade_date"])
    if data.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("universe contains duplicate trade_date/symbol rows")
    if not data["selected"].isin([0, 1]).all():
        raise ValueError("universe selected must contain only 0 or 1")
    return data.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def attach_point_in_time_eligibility(
    data: pd.DataFrame,
    *,
    symbol: str,
    universe: pd.DataFrame,
) -> pd.DataFrame:
    """Attach eligibility using the latest universe snapshot strictly before each bar.

    A month-end universe snapshot uses that day's closing information, so it
    becomes eligible only on the following trading bar. This one-bar delay is
    intentional anti-look-ahead protection.
    """

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data index must be a DatetimeIndex")
    symbol_rows = universe.loc[
        (universe["symbol"] == symbol) & (universe["selected"] == 1),
        ["trade_date", "selected"],
    ].sort_values("trade_date")
    left = pd.DataFrame({"date": data.index})
    eligible = (
        pd.merge_asof(
            left,
            symbol_rows.rename(columns={"trade_date": "snapshot_date"}),
            left_on="date",
            right_on="snapshot_date",
            direction="backward",
            allow_exact_matches=False,
        )["selected"]
        .fillna(0)
        .eq(1)
    )
    result = data.copy()
    result["pit_eligible"] = eligible.to_numpy()
    return result


def load_industry_changes(path: str | Path) -> pd.DataFrame:
    """Load historical industry memberships with explicit effective intervals."""

    data = pd.read_parquet(path).copy()
    required = {
        "symbol",
        "effective_date",
        "end_date",
        "industry_code",
        "industry_name",
    }
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"industry changes are missing columns: {', '.join(missing)}")
    data["effective_date"] = _as_trade_dates(data["effective_date"])
    data["end_date"] = pd.to_datetime(
        data["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    )
    data = data.sort_values(["symbol", "effective_date", "end_date"])
    previous_end = data.groupby("symbol")["end_date"].shift()
    overlapping = previous_end.notna() & (data["effective_date"] <= previous_end)
    if overlapping.any():
        raise ValueError("industry history contains overlapping membership intervals")
    return data.reset_index(drop=True)


def attach_industry_asof(
    data: pd.DataFrame,
    *,
    symbol: str,
    industry_changes: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the industry active on each bar, leaving uncovered bars as null."""

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data index must be a DatetimeIndex")
    memberships = industry_changes.loc[
        industry_changes["symbol"] == symbol,
        ["effective_date", "end_date", "industry_code", "industry_name"],
    ].sort_values("effective_date")
    left = pd.DataFrame({"date": data.index})
    matched = pd.merge_asof(
        left,
        memberships,
        left_on="date",
        right_on="effective_date",
        direction="backward",
    )
    active = matched["end_date"].isna() | (matched["date"] <= matched["end_date"])
    result = data.copy()
    result["industry_code"] = matched["industry_code"].where(active).to_numpy()
    result["industry_name"] = matched["industry_name"].where(active).to_numpy()
    return result


def load_market_context(path: str | Path, *, index_code: str) -> pd.DataFrame:
    """Load one broad-index daily series as an explicitly named volume proxy."""

    data = pd.read_parquet(path)
    required = {"ts_code", "trade_date", "close", "vol"}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"market index data is missing columns: {', '.join(missing)}")
    result = data.loc[
        data["ts_code"] == index_code, ["trade_date", "close", "vol"]
    ].copy()
    if result.empty:
        raise ValueError(f"market index {index_code} is absent")
    result["date"] = _as_trade_dates(result.pop("trade_date"))
    result = result.rename(columns={"close": "market_close", "vol": "market_volume"})
    return result.set_index("date").sort_index()


def attach_market_context(
    data: pd.DataFrame, market_context: pd.DataFrame
) -> pd.DataFrame:
    """Left-join market context by trading date without filling missing dates."""

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data index must be a DatetimeIndex")
    return data.join(market_context[["market_close", "market_volume"]], how="left")


def load_industry_etf_context(path: str | Path) -> pd.DataFrame:
    """Load the audited ETF-composite industry context by trading date."""

    data = pd.read_parquet(path).copy()
    required = {
        "trade_date",
        "industry_code",
        "sector_close",
        "sector_ma20",
        "sector_ma60",
        "sector_strong",
    }
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"industry ETF context is missing columns: {', '.join(missing)}")
    data["trade_date"] = _as_trade_dates(data["trade_date"])
    if data.duplicated(["trade_date", "industry_code"]).any():
        raise ValueError("industry ETF context contains duplicate date/industry rows")
    if not data["sector_strong"].dropna().isin([True, False]).all():
        raise ValueError("industry ETF context sector_strong must be boolean")
    return data.sort_values(["trade_date", "industry_code"]).reset_index(drop=True)


def attach_industry_etf_context(
    data: pd.DataFrame,
    *,
    industry_code: str,
    industry_context: pd.DataFrame,
) -> pd.DataFrame:
    """Attach same-day ETF context, which becomes tradable after that close."""

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data index must be a DatetimeIndex")
    selected = industry_context.loc[
        industry_context["industry_code"] == industry_code,
        ["trade_date", "sector_close", "sector_ma20", "sector_ma60", "sector_strong"],
    ].copy()
    selected = selected.rename(columns={"trade_date": "date"}).set_index("date")
    selected = selected.rename(
        columns={
            "sector_close": "sector_close",
            "sector_ma20": "sector_ma20",
            "sector_ma60": "sector_ma60",
            "sector_strong": "industry_regime",
        }
    )
    return data.join(selected, how="left")
