from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


def _daily_frame(stock: Mapping[str, Any]) -> pd.DataFrame:
    rows = stock.get("daily")
    if not isinstance(rows, Sequence) or not rows:
        return pd.DataFrame(columns=["date", "close", "high", "low"])
    frame = pd.DataFrame([row for row in rows if isinstance(row, Mapping)])
    if not {"date", "close"} <= set(frame.columns):
        return pd.DataFrame(columns=["date", "close", "high", "low"])
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ("close", "high", "low"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            frame[column] = frame["close"]
    frame.dropna(subset=["date", "close"], inplace=True)
    frame.sort_values("date", inplace=True)
    return frame[["date", "close", "high", "low"]].drop_duplicates("date", keep="last")


def _pair_observation(
    stock: Mapping[str, Any],
    peer: Mapping[str, Any],
) -> dict[str, Any] | None:
    left = _daily_frame(stock).rename(
        columns={"close": "close_left", "high": "high_left", "low": "low_left"}
    )
    right = _daily_frame(peer).rename(
        columns={"close": "close_right", "high": "high_right", "low": "low_right"}
    )
    joined = left.merge(right, on="date", how="inner")
    if len(joined) < 21:
        return None
    joined = joined.tail(21).copy()
    left_returns = joined["close_left"].pct_change().dropna()
    right_returns = joined["close_right"].pct_change().dropna()
    if len(left_returns) < 20 or len(right_returns) < 20:
        return None
    correlation = float(left_returns.corr(right_returns))
    if pd.isna(correlation):
        return None

    left_rs = float(joined["close_left"].iloc[-1] / joined["close_left"].iloc[0] - 1)
    right_rs = float(joined["close_right"].iloc[-1] / joined["close_right"].iloc[0] - 1)

    previous = joined.iloc[:-1]
    last = joined.iloc[-1]
    left_new_high = float(last["high_left"]) >= float(previous["high_left"].max())
    right_new_high = float(last["high_right"]) >= float(previous["high_right"].max())
    left_new_low = float(last["low_left"]) <= float(previous["low_left"].min())
    right_new_low = float(last["low_right"]) <= float(previous["low_right"].min())

    if correlation >= 0:
        confirmed = (left_new_high and right_new_high) or (left_new_low and right_new_low)
        diverged = (left_new_high and not right_new_high) or (
            left_new_low and not right_new_low
        )
    else:
        confirmed = (left_new_high and right_new_low) or (left_new_low and right_new_high)
        diverged = (left_new_high and not right_new_low) or (
            left_new_low and not right_new_high
        )

    if confirmed:
        confirmation = "confirmed"
    elif diverged:
        confirmation = "diverged"
    else:
        confirmation = "unknown"

    return {
        "peer": str(peer.get("code") or ""),
        "correlation20": correlation,
        "relativeStrength20": left_rs - right_rs,
        "extremeConfirmation": confirmation,
        "relativeExtremeDivergence": confirmation == "diverged",
    }


def build_intermarket_observations(
    stocks: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        str(stock.get("code") or ""): [] for stock in stocks
    }
    for index, stock in enumerate(stocks):
        candidates: list[tuple[float, dict[str, Any]]] = []
        for peer_index, peer in enumerate(stocks):
            if index == peer_index:
                continue
            observation = _pair_observation(stock, peer)
            if observation is None:
                continue
            candidates.append((abs(float(observation["correlation20"])), observation))
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0], reverse=True)
        result[str(stock.get("code") or "")] = [candidates[0][1]]
    return result
