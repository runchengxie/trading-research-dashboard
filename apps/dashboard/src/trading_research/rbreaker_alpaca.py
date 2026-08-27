"""Alpaca market-data helpers for reproducible R-Breaker input artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import date, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from trading_research.rbreaker_artifact import load_artifact

NEW_YORK = ZoneInfo("America/New_York")
SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)


def expected_regular_session_bars(session_date: date) -> int:
    """Return the expected one-minute bar count for an NYSE session."""

    import exchange_calendars as xcals

    schedule = xcals.get_calendar("XNYS").schedule.loc[str(session_date) : str(session_date)]
    if schedule.empty:
        raise ValueError(f"{session_date} is not an NYSE trading session")
    opening = schedule.iloc[0]["open"].tz_convert(NEW_YORK)
    closing = schedule.iloc[0]["close"].tz_convert(NEW_YORK)
    return int((closing - opening).total_seconds() // 60)


def _timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("Alpaca timestamps must be timezone-aware")
    return timestamp.tz_convert(NEW_YORK)


def normalize_regular_session_bars(
    bars: Iterable[Any], *, session_date: date
) -> pd.DataFrame:
    """Convert Alpaca bars to the artifact format and keep regular-session bars."""

    rows: list[dict[str, Any]] = []
    for bar in bars:
        timestamp = _timestamp(bar.timestamp)
        if timestamp.date() != session_date:
            continue
        if not SESSION_OPEN <= timestamp.time() < SESSION_CLOSE:
            continue
        rows.append(
            {
                "datetime": timestamp,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
            }
        )
    if not rows:
        raise ValueError(f"Alpaca returned no regular-session bars for {session_date}")
    frame = pd.DataFrame(rows).sort_values("datetime")
    if frame["datetime"].duplicated().any():
        raise ValueError("Alpaca bars contain duplicate timestamps")
    return frame.set_index("datetime")


def validate_regular_session_bars(
    bars: pd.DataFrame, *, expected_bars: int = 390
) -> None:
    """Reject an incomplete or non-continuous full US trading session."""

    if len(bars) != expected_bars:
        raise ValueError(
            f"regular session contains {len(bars)} bars, expected {expected_bars}"
        )
    deltas = bars.index.to_series().diff().dropna()
    if not (deltas == pd.Timedelta(minutes=1)).all():
        raise ValueError("regular-session bars are not continuous at one-minute intervals")


def extract_previous_day_ohlc(
    daily_bars: Iterable[Any], *, session_date: date
) -> dict[str, float]:
    """Select the latest daily bar before the requested New York session."""

    candidates: list[tuple[date, Any]] = []
    for bar in daily_bars:
        local_date = _timestamp(bar.timestamp).date()
        if local_date < session_date:
            candidates.append((local_date, bar))
    if not candidates:
        raise ValueError(f"Alpaca returned no previous daily bar for {session_date}")
    _, bar = max(candidates, key=lambda item: item[0])
    return {"high": float(bar.high), "low": float(bar.low), "close": float(bar.close)}


def write_alpaca_artifact(
    output_root: str | Path,
    *,
    symbol: str,
    bars: pd.DataFrame,
    previous_day: dict[str, float],
    data_start: str,
    data_end: str,
    generated_at: str,
    producer_commit: str,
) -> Path:
    """Write one normalized Alpaca symbol and a validated input manifest."""

    root = Path(output_root)
    bars_dir = root / "bars"
    bars_dir.mkdir(parents=True, exist_ok=True)
    normalized_symbol = symbol.upper()
    if not normalized_symbol.endswith(".US"):
        normalized_symbol = f"{normalized_symbol}.US"
    frame = bars.reset_index()
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.tz_localize(None)
    relative = f"bars/{normalized_symbol.lower()}.parquet"
    target = root / relative
    frame.to_parquet(target, index=False)
    manifest = {
        "schemaVersion": "trading_research.rbreaker_input.v1",
        "symbol": normalized_symbol,
        "dataStart": data_start,
        "dataEnd": data_end,
        "barInterval": "1m",
        "source": "alpaca",
        "generatedAt": generated_at,
        "producerCommit": producer_commit,
        "previousDay": previous_day,
        "files": [
            {
                "path": relative,
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        ],
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    load_artifact(root)
    return root
