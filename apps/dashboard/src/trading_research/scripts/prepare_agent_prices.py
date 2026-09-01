from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, cast

import pandas as pd

DEFAULT_SYMBOLS = ("510300.SH", "512100.SH", "159915.SZ", "511010.SH")


def _normalise_daily_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "close" in frame.columns:
        result = frame[[column for column in ("trade_date", "close") if column in frame]].copy()
        result = result.rename(columns={"trade_date": "date", "close": "Close"})
        result["date"] = pd.to_datetime(result["date"], format="%Y%m%d", errors="coerce")
        return result.dropna(subset=["date"])
    result = frame.copy()
    result["date"] = pd.to_datetime(result.index, errors="coerce")
    result["Close"] = pd.to_numeric(result.get("Close"), errors="coerce")
    return result.dropna(subset=["date"])


def build_price_payload(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    prices: dict[str, float] = {}
    previous_closes: dict[str, float] = {}
    dates: list[pd.Timestamp] = []
    for symbol, frame in frames.items():
        is_tushare_frame = "trade_date" in frame.columns
        normalised = _normalise_daily_frame(frame)
        if "Close" not in normalised.columns:
            continue
        normalised = normalised.sort_values("date")
        closes = pd.to_numeric(normalised["Close"], errors="coerce").dropna()
        if closes.empty:
            continue
        prices[symbol] = float(closes.iloc[-1])
        latest = pd.Timestamp(normalised.loc[closes.index[-1], "date"])
        if pd.isna(latest):
            continue
        dates.append(cast(pd.Timestamp, latest))
        if is_tushare_frame and len(closes) > 1:
            previous_closes[symbol] = float(closes.iloc[-2])
    if not prices or not dates:
        raise ValueError("price provider returned no valid close data")
    as_of = min(dates).strftime("%Y-%m-%d")
    if any(date.strftime("%Y-%m-%d") != as_of for date in dates):
        raise ValueError("price provider returned inconsistent trading dates")
    payload: dict[str, Any] = {"asOf": as_of, "prices": prices}
    if previous_closes:
        payload["previousCloses"] = previous_closes
    return payload


def fetch_prices(symbols: tuple[str, ...]) -> dict[str, Any]:
    from trading_research.data.data_sources import get_tushare_client

    token_env = "TUSHARE_TOKEN_2" if os.environ.get("TUSHARE_TOKEN_2") else "TUSHARE_TOKEN"
    client = get_tushare_client(token_env=token_env)
    end_date = pd.Timestamp.now(tz="Asia/Shanghai").strftime("%Y%m%d")
    start_date = (pd.Timestamp.now(tz="Asia/Shanghai") - pd.Timedelta(days=30)).strftime("%Y%m%d")
    frames = {
        symbol: client.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
        for symbol in symbols
    }
    return build_price_payload(frames)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch close prices for the Agent paper portfolio")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    symbols = tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip())
    payload = fetch_prices(symbols)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
