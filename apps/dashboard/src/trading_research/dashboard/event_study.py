from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
from research_core import EVENT_STUDY_VERSION


def _frame(stock: Mapping[str, Any]) -> pd.DataFrame:
    rows = stock.get("intraday")
    if not isinstance(rows, Sequence) or not rows:
        return pd.DataFrame(columns=["time", "price"])
    frame = pd.DataFrame([row for row in rows if isinstance(row, Mapping)])
    if "time" not in frame.columns or "price" not in frame.columns:
        return pd.DataFrame(columns=["time", "price"])
    frame = frame[["time", "price"]].copy()
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame.dropna(subset=["time", "price"], inplace=True)
    frame.sort_values("time", inplace=True)
    return frame.reset_index(drop=True)


def _price_at_or_before(frame: pd.DataFrame, timestamp: pd.Timestamp) -> float | None:
    rows = frame[frame["time"] <= timestamp]
    if rows.empty:
        return None
    return float(rows["price"].iloc[-1])


def _price_at_or_after(frame: pd.DataFrame, timestamp: pd.Timestamp) -> float | None:
    rows = frame[frame["time"] >= timestamp]
    if rows.empty:
        return None
    return float(rows["price"].iloc[0])


def _return(base: float | None, target: float | None) -> float | None:
    if base in (None, 0) or target is None:
        return None
    return target / base - 1


def build_event_studies(
    stock: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    *,
    pre_window_minutes: int = 60,
    post_window_minutes: int = 60,
) -> list[dict[str, Any]]:
    frame = _frame(stock)
    if frame.empty:
        return []

    instrument = str(stock.get("code") or "")
    data_date = str(stock.get("lastTradeDay") or "")
    studies: list[dict[str, Any]] = []
    for event in events:
        try:
            timestamp = pd.Timestamp(str(event["timestamp"]))
            event_id = str(event["id"])
            category = str(event["category"])
            importance = str(event.get("importance") or "medium")
        except (KeyError, TypeError, ValueError):
            continue
        if data_date and timestamp.strftime("%Y-%m-%d") != data_date:
            continue
        if importance not in {"low", "medium", "high"}:
            importance = "medium"

        base = _price_at_or_after(frame, timestamp)
        pre = _price_at_or_before(
            frame, timestamp - pd.Timedelta(minutes=pre_window_minutes)
        )
        r15 = _price_at_or_after(frame, timestamp + pd.Timedelta(minutes=15))
        r30 = _price_at_or_after(frame, timestamp + pd.Timedelta(minutes=30))
        r60 = _price_at_or_after(frame, timestamp + pd.Timedelta(minutes=60))
        first5 = _price_at_or_after(frame, timestamp + pd.Timedelta(minutes=5))

        pre_window = frame[
            (frame["time"] >= timestamp - pd.Timedelta(minutes=pre_window_minutes))
            & (frame["time"] <= timestamp)
        ]
        immediate = frame[
            (frame["time"] >= timestamp)
            & (frame["time"] <= timestamp + pd.Timedelta(minutes=5))
        ]
        post = frame[
            (frame["time"] >= timestamp)
            & (frame["time"] <= timestamp + pd.Timedelta(minutes=post_window_minutes))
        ]

        def range_pct(window: pd.DataFrame, denominator: float | None) -> float | None:
            if window.empty or denominator in (None, 0):
                return None
            return float(window["price"].max() - window["price"].min()) / denominator

        if post.empty or base in (None, 0):
            mfe = mae = None
        else:
            mfe = float(post["price"].max()) / base - 1
            mae = float(post["price"].min()) / base - 1

        first_move = _return(base, first5)
        final_move = _return(base, r60)
        reversal = None
        if first_move is not None and final_move is not None:
            reversal = (
                first_move != 0
                and final_move != 0
                and (first_move > 0) != (final_move > 0)
            )

        studies.append(
            {
                "schemaVersion": EVENT_STUDY_VERSION,
                "event": {
                    "id": event_id,
                    "category": category,
                    "importance": importance,
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "instrument": instrument,
                "dataDate": timestamp.strftime("%Y-%m-%d"),
                "preWindowMinutes": pre_window_minutes,
                "postWindowMinutes": post_window_minutes,
                "metrics": {
                    "preReturn": _return(pre, base),
                    "preRangePct": range_pct(pre_window, pre),
                    "immediateRangePct": range_pct(immediate, base),
                    "return15m": _return(base, r15),
                    "return30m": _return(base, r30),
                    "return60m": _return(base, r60),
                    "mfe60m": mfe,
                    "mae60m": mae,
                    "initialMoveReversal": reversal,
                },
                "provenance": {
                    "source": "provided-event-input",
                    "definitionVersion": "event-study.v1",
                },
            }
        )
    return studies
