"""Build a validated US R-Breaker input artifact from Alpaca history."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from trading_research.rbreaker_alpaca import (
    NEW_YORK,
    SESSION_CLOSE,
    SESSION_OPEN,
    extract_previous_day_ohlc,
    normalize_regular_session_bars,
    validate_regular_session_bars,
    write_alpaca_artifact,
)

DEFAULT_DATA_ROOT = Path.home() / "data" / "trading-research-dashboard" / "rbreaker" / "alpaca"


def _response_bars(response: Any, symbol: str) -> list[Any]:
    return list(response[symbol])


def fetch_and_write_artifact(
    client: Any,
    *,
    symbol: str,
    session_date: date,
    output_root: str | Path,
    producer_commit: str,
    feed: Any = None,
    request_factory: Any = None,
    minute_timeframe: Any = None,
    daily_timeframe: Any = None,
    require_complete: bool = True,
) -> Path:
    """Fetch one US regular session and its previous daily bar."""

    normalized = symbol.upper().removesuffix(".US")
    if request_factory is None:
        from alpaca.data.enums import Adjustment, DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        request_factory = StockBarsRequest
        minute_timeframe = TimeFrame.Minute
        daily_timeframe = TimeFrame.Day
        feed = feed or DataFeed.SIP
        adjustment = Adjustment.ALL
    else:
        adjustment = "all"
    if feed is None:
        feed = "iex"
    session_start = datetime.combine(session_date, SESSION_OPEN, tzinfo=NEW_YORK)
    session_end = datetime.combine(session_date, SESSION_CLOSE, tzinfo=NEW_YORK)
    daily_start = session_start - timedelta(days=14)
    daily_end = session_start
    minute_response = client.get_stock_bars(
        request_factory(
            symbol_or_symbols=normalized,
            timeframe=minute_timeframe,
            start=session_start.astimezone(UTC),
            end=session_end.astimezone(UTC),
            adjustment=adjustment,
            feed=feed,
        )
    )
    daily_response = client.get_stock_bars(
        request_factory(
            symbol_or_symbols=normalized,
            timeframe=daily_timeframe,
            start=daily_start.astimezone(UTC),
            end=daily_end.astimezone(UTC),
            adjustment=adjustment,
            feed=feed,
        )
    )
    bars = normalize_regular_session_bars(
        _response_bars(minute_response, normalized), session_date=session_date
    )
    if require_complete:
        validate_regular_session_bars(bars)
    previous_day = extract_previous_day_ohlc(
        _response_bars(daily_response, normalized), session_date=session_date
    )
    return write_alpaca_artifact(
        output_root,
        symbol=f"{normalized}.US",
        bars=bars,
        previous_day=previous_day,
        data_start=session_start.isoformat(),
        data_end=session_end.isoformat(),
        generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        producer_commit=producer_commit,
    )


def _credentials() -> tuple[str, str]:
    key = os.getenv("APCA_API_KEY_ID", "").strip()
    secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
    if key and secret:
        return key, secret
    path = os.getenv("API_KEYS_PATH", "").strip()
    if path:
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        key = str(payload.get("alpaca_key_id", "")).strip()
        secret = str(payload.get("alpaca_secret", "")).strip()
    if not key or not secret:
        raise RuntimeError(
            "set APCA_API_KEY_ID/APCA_API_SECRET_KEY or API_KEYS_PATH with Alpaca credentials"
        )
    return key, secret


def default_output_root(symbol: str, session_date: date) -> Path:
    """Return the persistent local output directory for one symbol and session."""

    normalized = symbol.upper().removesuffix(".US")
    return DEFAULT_DATA_ROOT / f"{normalized}.US" / session_date.isoformat()


def main() -> None:
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical import StockHistoricalDataClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="US ticker, for example AAPL or TSLA")
    parser.add_argument("--session-date", required=True, type=date.fromisoformat)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--producer-commit", default=os.getenv("GITHUB_SHA", "local"))
    parser.add_argument("--feed", choices=("iex", "sip"), default="sip")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="allow missing minutes for halted or shortened sessions",
    )
    args = parser.parse_args()
    key, secret = _credentials()
    feed = DataFeed.SIP if args.feed == "sip" else DataFeed.IEX
    output_root = args.output_root or default_output_root(args.symbol, args.session_date)
    fetch_and_write_artifact(
        StockHistoricalDataClient(key, secret),
        symbol=args.symbol,
        session_date=args.session_date,
        output_root=output_root,
        producer_commit=args.producer_commit,
        feed=feed,
        require_complete=not args.allow_incomplete,
    )


if __name__ == "__main__":
    main()
