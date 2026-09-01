from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

DEFAULT_SYMBOLS = ("SPY", "QQQ", "TLT", "GLD")


def build_price_payload(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    prices: dict[str, float] = {}
    dates: list[pd.Timestamp] = []
    for symbol, frame in frames.items():
        if "Close" not in frame.columns:
            continue
        closes = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if closes.empty:
            continue
        prices[symbol] = float(closes.iloc[-1])
        latest = pd.Timestamp(closes.index[-1])
        if pd.isna(latest):
            continue
        dates.append(cast(pd.Timestamp, latest))
    if not prices or not dates:
        raise ValueError("price provider returned no valid close data")
    as_of = min(dates).strftime("%Y-%m-%d")
    if any(date.strftime("%Y-%m-%d") != as_of for date in dates):
        raise ValueError("price provider returned inconsistent trading dates")
    return {"asOf": as_of, "prices": prices}


def fetch_prices(symbols: tuple[str, ...]) -> dict[str, Any]:
    import yfinance as yf

    frames = {
        symbol: yf.Ticker(symbol).history(period="10d", auto_adjust=False)
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
