"""Runtime CSV cache helpers for Dashboard market data."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def cache_path(
    root: str,
    kind: str,
    code: str,
    *,
    trade_date: str | None = None,
) -> str:
    if kind == "intraday":
        if trade_date is None:
            raise ValueError("intraday cache requires trade_date")
        compact_date = pd.Timestamp(trade_date).strftime("%Y%m%d")
        return os.path.join(root, kind, code, f"{compact_date}.csv")
    return os.path.join(root, kind, f"{code}.csv")


def write_cache(
    root: str,
    kind: str,
    code: str,
    frame: pd.DataFrame,
    *,
    trade_date: str | None = None,
) -> None:
    path = cache_path(root, kind, code, trade_date=trade_date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frame.to_csv(path, index=False)


def read_cache(
    root: str,
    kind: str,
    code: str,
    *,
    trade_date: str | None = None,
) -> pd.DataFrame:
    path = Path(cache_path(root, kind, code, trade_date=trade_date))
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
