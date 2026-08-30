"""Build validated contextual snapshots from historical dashboard bars.

The checked-in Dashboard payload keeps only the latest intraday session.  This
utility reuses its daily history and asks the configured CN data provider for
older intraday sessions, producing the validated inputs consumed by
``enrich_contextual_research --history``.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from trading_research.dashboard.contextual_research import build_contextual_snapshot
from trading_research.dashboard.indicators import calculate_atr, calculate_vwap, get_opening_range
from trading_research.data import market_compat as data_sources

IntradayFetcher = Callable[[str, str], pd.DataFrame]


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def _daily_frame(stock: Mapping[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(stock.get("daily", []))
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required <= set(frame.columns):
        return pd.DataFrame(columns=sorted(required))
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in required - {"date"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date", "high", "low", "close"]).sort_values("date")


def _historical_stock(
    stock: Mapping[str, Any],
    *,
    data_date: str,
    fetch_intraday: IntradayFetcher,
) -> dict[str, Any]:
    code = str(stock.get("code") or "")
    bars = fetch_intraday(code, data_date)
    if bars is None or bars.empty:
        raise ValueError(f"{code} {data_date}: intraday bars are empty")
    required = {"time", "price", "volume"}
    if not required <= set(bars.columns):
        raise ValueError(f"{code} {data_date}: intraday bars missing {sorted(required - set(bars.columns))}")

    historical = copy.deepcopy(dict(stock))
    daily = _daily_frame(stock)
    timestamped = bars[["time", "price", "volume"]].copy()
    timestamped["time"] = pd.to_datetime(
        data_date + " " + timestamped["time"].astype(str), errors="coerce"
    )
    timestamped["price"] = pd.to_numeric(timestamped["price"], errors="coerce")
    timestamped["volume"] = pd.to_numeric(timestamped["volume"], errors="coerce")
    timestamped = timestamped.dropna(subset=["time", "price"]).sort_values("time")
    historical["lastTradeDay"] = data_date
    historical["intraday"] = [
        {
            "time": row.time.strftime("%Y-%m-%d %H:%M:%S"),
            "price": float(row.price),
            "volume": 0 if pd.isna(row.volume) else int(row.volume),
        }
        for row in timestamped.itertuples(index=False)
    ]

    prior = daily[daily["date"] < pd.Timestamp(data_date)].copy()
    indicators = dict(historical.get("indicators") or {})
    if len(prior) >= 20:
        indicators["atr20"] = _number(calculate_atr(prior.copy(), 20))
        previous = prior.iloc[-1]
        indicators["lastClose"] = _number(previous["close"])
        indicators["yesterdayHigh"] = _number(previous["high"])
        indicators["yesterdayLow"] = _number(previous["low"])
    else:
        indicators["atr20"] = None
    indicators["vwap"] = _number(calculate_vwap(timestamped.copy()))
    orb_high, orb_low = get_opening_range(timestamped.copy())
    indicators["orbHigh"] = _number(orb_high)
    indicators["orbLow"] = _number(orb_low)
    historical["indicators"] = indicators
    # Current clustered levels are not point-in-time historical levels.
    historical["levels"] = []
    return historical


def build_history(
    document: Mapping[str, Any],
    *,
    sessions: int,
    codes: Sequence[str] | None = None,
    fetch_intraday: IntradayFetcher | None = None,
) -> list[dict[str, Any]]:
    if sessions <= 0:
        raise ValueError("sessions must be positive")
    stocks = document.get("stocks")
    if not isinstance(stocks, list):
        raise ValueError("dashboard document requires stocks array")
    selected = set(codes or ())
    fetcher = fetch_intraday or (
        lambda code, data_date: data_sources.fetch_intraday(code, data_date)
    )
    snapshots: list[dict[str, Any]] = []
    for stock in stocks:
        if not isinstance(stock, Mapping):
            continue
        code = str(stock.get("code") or "")
        if selected and code not in selected:
            continue
        daily = _daily_frame(stock)
        current_date = pd.to_datetime(str(stock.get("lastTradeDay") or ""), errors="coerce")
        if pd.isna(current_date):
            current_date = daily["date"].max() if not daily.empty else pd.NaT
        dates = daily.loc[daily["date"] < current_date, "date"].drop_duplicates().tail(sessions)
        for timestamp in dates:
            data_date = timestamp.strftime("%Y-%m-%d")
            historical_stock = _historical_stock(
                stock, data_date=data_date, fetch_intraday=fetcher
            )
            snapshots.append(
                build_contextual_snapshot([historical_stock], generated_at=data_date)
            )
    if not snapshots:
        raise ValueError("no historical contextual snapshots were generated")
    return snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sessions", type=int, default=20)
    parser.add_argument("--codes", default="", help="comma-separated instrument codes")
    args = parser.parse_args()

    document = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("dashboard document root must be an object")
    codes = [item.strip() for item in args.codes.split(",") if item.strip()]
    snapshots = build_history(document, sessions=args.sessions, codes=codes or None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"generated_contextual_snapshots={len(snapshots)} output={args.output}")


if __name__ == "__main__":
    main()
