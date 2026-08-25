from __future__ import annotations

from pathlib import Path

import pandas as pd


_REQUIRED_CLEAN_COLUMNS = {
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "vol",
    "amount",
}

_OPTIONAL_EXECUTION_COLUMNS = (
    "up_limit",
    "down_limit",
    "is_limit_up",
    "is_limit_down",
    "is_suspended",
    "is_st",
)


def load_tushare_daily_clean(
    root: str | Path,
    symbol: str,
    *,
    adjusted: bool = True,
    exclude_suspended: bool = True,
) -> pd.DataFrame:
    """Load one symbol from the platform's per-symbol daily-clean Parquet asset.

    The loader deliberately requires the named daily-clean dataset rather than
    globbing arbitrary provider files. With ``adjusted=True`` it uses the
    dataset's ``adj_*`` OHLC fields, while preserving native ``vol`` and
    ``amount`` as ``volume`` and ``amount``. In the current TuShare contract,
    volume is in hands and amount is in thousand CNY; callers using
    ``cost_line_proxy`` should therefore use ``amount_scale=10``.
    """

    root = Path(root).expanduser()
    path = root / "data" / f"{symbol}.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"daily-clean file not found for {symbol}: {path}")
    raw = pd.read_parquet(path)
    missing = sorted(_REQUIRED_CLEAN_COLUMNS.difference(raw.columns))
    if missing:
        raise ValueError(f"daily-clean asset missing columns: {', '.join(missing)}")

    source_columns = ["open", "high", "low", "close"]
    if adjusted:
        source_columns = [f"adj_{column}" for column in source_columns]
        absent = [column for column in source_columns if column not in raw.columns]
        if absent:
            raise ValueError(
                "daily-clean asset lacks adjusted OHLC columns: " + ", ".join(absent)
            )
    result = raw.loc[:, ["trade_date", *source_columns, "vol", "amount"]].copy()
    result.columns = ["date", "open", "high", "low", "close", "volume", "amount"]
    for column in _OPTIONAL_EXECUTION_COLUMNS:
        if column in raw.columns:
            result[column] = raw[column]
    if adjusted and {"adj_close", "close"}.issubset(raw.columns):
        adjustment_multiplier = raw["adj_close"] / raw["close"]
        for column in ("up_limit", "down_limit"):
            if column in result.columns:
                result[column] = result[column] * adjustment_multiplier
    result["date"] = pd.to_datetime(result["date"].astype(str), format="%Y%m%d")
    if exclude_suspended and "is_suspended" in raw.columns:
        result = result.loc[~raw["is_suspended"].fillna(False)].copy()
    result = result.dropna(subset=["open", "high", "low", "close", "volume"])
    result = (
        result.sort_values("date")
        .drop_duplicates("date", keep="last")
        .set_index("date")
    )
    if not result.index.is_monotonic_increasing or result.index.has_duplicates:
        raise ValueError("daily-clean dates must be unique and ascending")
    if len(result) < 2:
        raise ValueError(f"insufficient usable bars for {symbol}")
    return result
