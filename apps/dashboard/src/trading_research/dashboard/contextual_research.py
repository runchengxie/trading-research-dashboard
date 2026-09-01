from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import time
from typing import Any, cast

import pandas as pd
from research_core import (
    CONTEXTUAL_SNAPSHOT_VERSION,
    MARKET_CONTEXT_VERSION,
    SETUP_EVENT_VERSION,
    validate_contextual_snapshot,
)

SESSION_WINDOWS: dict[str, tuple[tuple[str, time, time], ...]] = {
    "US": (
        ("premarket", time(4, 0), time(9, 30)),
        ("opening_range", time(9, 30), time(10, 30)),
        ("morning", time(10, 30), time(12, 0)),
        ("midday", time(12, 0), time(13, 30)),
        ("afternoon", time(13, 30), time(15, 0)),
        ("power_hour", time(15, 0), time(16, 0)),
    ),
    "CN": (
        ("open", time(9, 30), time(10, 0)),
        ("morning", time(10, 0), time(11, 30)),
        ("afternoon_open", time(13, 0), time(14, 0)),
        ("afternoon", time(14, 0), time(14, 45)),
        ("close", time(14, 45), time(15, 0)),
    ),
    "HK": (
        ("open", time(9, 30), time(10, 0)),
        ("morning", time(10, 0), time(12, 0)),
        ("afternoon_open", time(13, 0), time(14, 0)),
        ("afternoon", time(14, 0), time(15, 30)),
        ("close", time(15, 30), time(16, 0)),
    ),
}

_INDICATOR_LEVELS: tuple[tuple[str, str, str], ...] = (
    ("orbHigh", "opening_range_high", "开盘区间高点"),
    ("orbLow", "opening_range_low", "开盘区间低点"),
    ("vwap", "vwap", "VWAP（日终上下文）"),
)
_POINT_IN_TIME_LEVEL_KINDS = {
    "previous_day_high",
    "previous_day_low",
    "previous_5d_high",
    "previous_5d_low",
    "opening_range_high",
    "opening_range_low",
}
_ORB_AVAILABLE_FROM = {
    "US": time(10, 30),
    "CN": time(10, 0),
    "HK": time(10, 0),
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def _timestamp(value: Any) -> pd.Timestamp | None:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    return cast(pd.Timestamp, timestamp)


def _intraday_frame(stock: Mapping[str, Any]) -> pd.DataFrame:
    rows = stock.get("intraday")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return pd.DataFrame(columns=["time", "price"])
    frame = pd.DataFrame([row for row in rows if isinstance(row, Mapping)])
    if "time" not in frame.columns or "price" not in frame.columns:
        return pd.DataFrame(columns=["time", "price"])
    frame = frame[[column for column in ("time", "price", "volume") if column in frame]].copy()
    if "volume" not in frame.columns:
        frame["volume"] = pd.NA
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    frame.dropna(subset=["time", "price"], inplace=True)
    frame.sort_values("time", inplace=True)
    return frame.reset_index(drop=True)


def _daily_frame(stock: Mapping[str, Any]) -> pd.DataFrame:
    rows = stock.get("daily")
    columns = ["date", "open", "high", "low", "close"]
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame([row for row in rows if isinstance(row, Mapping)])
    if not {"date", "high", "low", "close"} <= set(frame.columns):
        return pd.DataFrame(columns=columns)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in ("open", "high", "low", "close"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame.dropna(subset=["date", "high", "low", "close"], inplace=True)
    frame.sort_values("date", inplace=True)
    return frame.drop_duplicates("date", keep="last").reset_index(drop=True)


def _reference_date(stock: Mapping[str, Any]) -> pd.Timestamp | None:
    intraday = _intraday_frame(stock)
    if not intraday.empty:
        timestamp = _timestamp(intraday["time"].iloc[0])
        return None if timestamp is None else timestamp.normalize()
    value = stock.get("lastTradeDay")
    if isinstance(value, str) and value:
        timestamp = _timestamp(pd.to_datetime(value, errors="coerce"))
        if timestamp is not None:
            return timestamp.normalize()
    return None


def _prior_daily(stock: Mapping[str, Any]) -> pd.DataFrame:
    frame = _daily_frame(stock)
    reference_date = _reference_date(stock)
    if frame.empty or reference_date is None:
        return frame.iloc[0:0]
    return frame[frame["date"] < reference_date].copy()


def _current_price(stock: Mapping[str, Any]) -> float | None:
    intraday = _intraday_frame(stock)
    if not intraday.empty:
        return float(intraday["price"].iloc[-1])
    indicators = stock.get("indicators")
    if isinstance(indicators, Mapping):
        return _number(indicators.get("lastClose"))
    return None


def session_for_timestamp(
    timestamp: str | pd.Timestamp,
    market: str,
    timezone: str,
) -> str | None:
    value = _timestamp(timestamp)
    if value is None:
        return None
    if value.tzinfo is not None and timezone:
        try:
            value = value.tz_convert(timezone)
        except (TypeError, ValueError):
            pass
    current = value.time()
    for session_id, start, end in SESSION_WINDOWS.get(market.upper(), ()):
        if start <= current < end:
            return session_id
    return None


def semantic_reference_levels(stock: Mapping[str, Any]) -> list[dict[str, Any]]:
    current = _current_price(stock)
    levels: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()

    def add(kind: str, value: Any, label: str) -> None:
        number = _number(value)
        if number is None:
            return
        key = (kind, round(number, 10))
        if key in seen:
            return
        seen.add(key)
        levels.append(
            {
                "kind": kind,
                "value": number,
                "distancePct": None if current in (None, 0) else (number - current) / current,
                "sourceLabel": label,
            }
        )

    prior = _prior_daily(stock)
    if not prior.empty:
        previous = prior.iloc[-1]
        add("previous_day_high", previous["high"], "前一交易日高点")
        add("previous_day_low", previous["low"], "前一交易日低点")
        trailing = prior.tail(5)
        add("previous_5d_high", trailing["high"].max(), "前 5 交易日高点")
        add("previous_5d_low", trailing["low"].min(), "前 5 交易日低点")
        reference_date = _reference_date(stock)
        if reference_date is not None:
            week_start = reference_date - pd.Timedelta(days=reference_date.weekday() + 7)
            week_end = week_start + pd.Timedelta(days=7)
            previous_week = prior[(prior["date"] >= week_start) & (prior["date"] < week_end)]
            if not previous_week.empty:
                add("previous_week_high", previous_week["high"].max(), "前一自然周高点")
                add("previous_week_low", previous_week["low"].min(), "前一自然周低点")

    indicators = stock.get("indicators")
    if isinstance(indicators, Mapping):
        for field, kind, label in _INDICATOR_LEVELS:
            add(kind, indicators.get(field), label)

    raw_levels = stock.get("levels")
    if isinstance(raw_levels, Sequence) and not isinstance(raw_levels, (str, bytes)):
        for raw in raw_levels:
            if not isinstance(raw, Mapping):
                continue
            kind = raw.get("type")
            if kind in {"support", "resistance", "key", "center"}:
                add(str(kind), raw.get("value"), str(raw.get("label") or kind))
    for summary in _session_summaries(stock):
        session_id = summary["id"]
        add("session_open", summary.get("open"), f"{session_id} 开盘")
        add("session_high", summary.get("high"), f"{session_id} 高点")
        add("session_low", summary.get("low"), f"{session_id} 低点")
    return levels


def _higher_timeframe_context(stock: Mapping[str, Any]) -> dict[str, Any]:
    prior = _prior_daily(stock).tail(20)
    if len(prior) < 20:
        return {"trend20": "insufficient_data", "return20": None, "rangePosition20": None}
    first_close = float(prior["close"].iloc[0])
    last_close = float(prior["close"].iloc[-1])
    return20 = None if first_close == 0 else last_close / first_close - 1
    if return20 is None:
        trend = "insufficient_data"
    elif return20 > 0.02:
        trend = "up"
    elif return20 < -0.02:
        trend = "down"
    else:
        trend = "flat"
    range_high = float(prior["high"].max())
    range_low = float(prior["low"].min())
    position = (
        0.5 if range_high <= range_low else (last_close - range_low) / (range_high - range_low)
    )
    position = min(1.0, max(0.0, position))
    return {"trend20": trend, "return20": return20, "rangePosition20": position}


def _session_summaries(stock: Mapping[str, Any]) -> list[dict[str, Any]]:
    frame = _intraday_frame(stock)
    if frame.empty:
        return []
    market = str(stock.get("market") or "CN")
    timezone = str(stock.get("timezone") or "")
    frame = frame.assign(
        session=[session_for_timestamp(ts, market, timezone) for ts in frame["time"]]
    )
    total_volume = frame["volume"].sum(min_count=1)
    total_volume = None if pd.isna(total_volume) else float(total_volume)
    summaries: list[dict[str, Any]] = []
    for session_id, group in frame.dropna(subset=["session"]).groupby("session", sort=False):
        first = float(group["price"].iloc[0])
        last = float(group["price"].iloc[-1])
        session_volume = group["volume"].sum(min_count=1)
        session_volume = None if pd.isna(session_volume) else float(session_volume)
        high_index = group["price"].idxmax()
        low_index = group["price"].idxmin()
        summaries.append(
            {
                "id": str(session_id),
                "open": first,
                "close": last,
                "high": float(group["price"].max()),
                "low": float(group["price"].min()),
                "returnPct": None if first == 0 else last / first - 1,
                "bars": int(len(group)),
                "volume": session_volume,
                "volumeShare": (
                    None
                    if session_volume is None or total_volume in (None, 0)
                    else session_volume / total_volume
                ),
                "highTimestamp": pd.Timestamp(group.loc[high_index, "time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "lowTimestamp": pd.Timestamp(group.loc[low_index, "time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        )
    return summaries


def _day_features(stock: Mapping[str, Any]) -> dict[str, Any]:
    frame = _intraday_frame(stock)
    indicators = stock.get("indicators")
    atr = _number(indicators.get("atr20")) if isinstance(indicators, Mapping) else None
    if len(frame) < 2:
        return {
            "rangeToAtr": None,
            "closeLocation": None,
            "intradayRangePct": None,
            "gapPct": None,
            "highTime": None,
            "lowTime": None,
        }
    high = float(frame["price"].max())
    low = float(frame["price"].min())
    first = float(frame["price"].iloc[0])
    close = float(frame["price"].iloc[-1])
    day_range = high - low
    prior = _prior_daily(stock)
    prior_close = None if prior.empty else _number(prior["close"].iloc[-1])
    high_time = pd.Timestamp(frame.loc[frame["price"].idxmax(), "time"]).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    low_time = pd.Timestamp(frame.loc[frame["price"].idxmin(), "time"]).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return {
        "rangeToAtr": None if not atr or atr <= 0 else day_range / atr,
        "closeLocation": 0.5 if day_range <= 0 else (close - low) / day_range,
        "intradayRangePct": None if first == 0 else day_range / first,
        "gapPct": None if prior_close in (None, 0) else first / prior_close - 1,
        "highTime": high_time,
        "lowTime": low_time,
    }


def classify_day_archetype(stock: Mapping[str, Any]) -> dict[str, Any]:
    frame = _intraday_frame(stock)
    if len(frame) < 6:
        return {
            "id": "insufficient_data",
            "reasons": ["至少需要 6 个有效分时点才能分类日型"],
        }

    features = _day_features(stock)
    close_location = features["closeLocation"]
    range_to_atr = features["rangeToAtr"]
    indicators = stock.get("indicators")
    orb_high = _number(indicators.get("orbHigh")) if isinstance(indicators, Mapping) else None
    orb_low = _number(indicators.get("orbLow")) if isinstance(indicators, Mapping) else None
    close = float(frame["price"].iloc[-1])
    high_idx = int(frame["price"].idxmax())
    low_idx = int(frame["price"].idxmin())
    n = len(frame)

    if (
        orb_high is not None
        and close > orb_high
        and close_location is not None
        and close_location >= 0.75
    ):
        return {
            "id": "opening_drive_up",
            "reasons": ["收盘保持在 ORB 高点上方", "收盘位于日内区间上四分位"],
        }
    if (
        orb_low is not None
        and close < orb_low
        and close_location is not None
        and close_location <= 0.25
    ):
        return {
            "id": "opening_drive_down",
            "reasons": ["收盘保持在 ORB 低点下方", "收盘位于日内区间下四分位"],
        }

    early_cutoff = max(1, int(n * 0.4))
    if close_location is not None:
        if high_idx < early_cutoff and close_location <= 0.35:
            return {"id": "morning_reversal", "reasons": ["日内高点较早形成", "收盘回到区间下部"]}
        if low_idx < early_cutoff and close_location >= 0.65:
            return {"id": "morning_reversal", "reasons": ["日内低点较早形成", "收盘回到区间上部"]}

    late_cutoff = max(1, int(n * 0.8))
    if close_location is not None and (
        (high_idx >= late_cutoff and close_location >= 0.75)
        or (low_idx >= late_cutoff and close_location <= 0.25)
    ):
        return {"id": "late_breakout", "reasons": ["日内极值在最后 20% 的分时样本中形成"]}

    if range_to_atr is not None and range_to_atr >= 1.0 and close_location is not None:
        if close_location >= 0.75:
            return {"id": "trend_up", "reasons": ["日内区间达到至少 1 ATR", "收盘靠近日内高位"]}
        if close_location <= 0.25:
            return {"id": "trend_down", "reasons": ["日内区间达到至少 1 ATR", "收盘靠近日内低位"]}

    return {"id": "range", "reasons": ["未满足趋势、开盘驱动、早盘反转或尾盘突破规则"]}


def build_market_context(stock: Mapping[str, Any], *, data_date: str) -> dict[str, Any]:
    market = str(stock.get("market") or "CN").upper()
    timezone = str(
        stock.get("timezone") or ("America/New_York" if market == "US" else "Asia/Shanghai")
    )
    return {
        "schemaVersion": MARKET_CONTEXT_VERSION,
        "instrument": {
            "code": str(stock.get("code") or ""),
            "name": str(stock.get("name") or stock.get("code") or ""),
        },
        "dataDate": data_date,
        "market": market,
        "timezone": timezone,
        "currentPrice": _current_price(stock),
        "referenceLevels": semantic_reference_levels(stock),
        "sessions": _session_summaries(stock),
        "higherTimeframe": _higher_timeframe_context(stock),
        "dayArchetype": classify_day_archetype(stock),
        "features": _day_features(stock),
        "intermarket": [],
        "provenance": {
            "source": "dashboard-data-json",
            "definitionVersion": "market-context.v1",
        },
    }


def _tolerance(level: float, stock: Mapping[str, Any]) -> float:
    indicators = stock.get("indicators")
    atr = _number(indicators.get("atr20")) if isinstance(indicators, Mapping) else None
    candidates = [abs(level) * 0.0005]
    if atr is not None and atr > 0:
        candidates.append(atr * 0.02)
    return max(candidates)


def _level_is_available(level: Mapping[str, Any], timestamp: pd.Timestamp, market: str) -> bool:
    kind = str(level.get("kind") or "")
    if kind not in _POINT_IN_TIME_LEVEL_KINDS:
        return False
    if kind.startswith("opening_range_"):
        available = _ORB_AVAILABLE_FROM.get(market.upper())
        return available is not None and timestamp.time() >= available
    return True


def _forward_price(frame: pd.DataFrame, start: pd.Timestamp, minutes: int) -> float | None:
    rows = frame[frame["time"] >= start + pd.Timedelta(minutes=minutes)]
    return None if rows.empty else float(rows["price"].iloc[0])


def _outcome(frame: pd.DataFrame, index: int) -> dict[str, float | None]:
    start_time = _timestamp(frame.loc[index, "time"])
    if start_time is None:
        return {
            "return5m": None,
            "return15m": None,
            "return30m": None,
            "mfe30m": None,
            "mae30m": None,
        }
    start_price = float(frame.loc[index, "price"])
    if start_price == 0:
        return {
            "return5m": None,
            "return15m": None,
            "return30m": None,
            "mfe30m": None,
            "mae30m": None,
        }

    def ret(minutes: int) -> float | None:
        price = _forward_price(frame, start_time, minutes)
        return None if price is None else price / start_price - 1

    window = frame[
        (frame["time"] >= start_time) & (frame["time"] <= start_time + pd.Timedelta(minutes=30))
    ]
    mfe = None if window.empty else float(window["price"].max()) / start_price - 1
    mae = None if window.empty else float(window["price"].min()) / start_price - 1
    return {
        "return5m": ret(5),
        "return15m": ret(15),
        "return30m": ret(30),
        "mfe30m": mfe,
        "mae30m": mae,
    }


def _event(
    *,
    stock: Mapping[str, Any],
    frame: pd.DataFrame,
    index: int,
    event_type: str,
    level: Mapping[str, Any],
    tolerance: float,
    context: Mapping[str, Any],
    trigger_bars: int,
) -> dict[str, Any]:
    timestamp = _timestamp(frame.loc[index, "time"])
    if timestamp is None:
        raise ValueError("setup event requires a valid timestamp")
    higher_timeframe = context.get("higherTimeframe")
    day_archetype = context.get("dayArchetype")
    return {
        "schemaVersion": SETUP_EVENT_VERSION,
        "instrument": str(stock.get("code") or ""),
        "dataDate": timestamp.strftime("%Y-%m-%d"),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "session": session_for_timestamp(
            timestamp,
            str(stock.get("market") or "CN"),
            str(stock.get("timezone") or ""),
        ),
        "eventType": event_type,
        "referenceLevel": {
            "kind": str(level["kind"]),
            "value": float(level["value"]),
            "sourceLabel": str(level["sourceLabel"]),
        },
        "observedPrice": float(frame.loc[index, "price"]),
        "tolerance": tolerance,
        "context": {
            "htfTrend": str(
                higher_timeframe.get("trend20")
                if isinstance(higher_timeframe, Mapping)
                else "unknown"
            ),
            "dayArchetype": str(
                day_archetype.get("id") if isinstance(day_archetype, Mapping) else "unknown"
            ),
            "rangePosition20": (
                higher_timeframe.get("rangePosition20")
                if isinstance(higher_timeframe, Mapping)
                else None
            ),
        },
        "trigger": {
            "kind": event_type,
            "barCount": trigger_bars,
            "tolerance": tolerance,
        },
        "outcome": _outcome(frame, index),
        "definitionVersion": "setup-detector.v1",
        "provenance": {"source": "dashboard-data-json-point-in-time"},
    }


def detect_setup_events(
    stock: Mapping[str, Any],
    context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    frame = _intraday_frame(stock)
    if len(frame) < 2:
        return []
    market = str(stock.get("market") or "CN")
    levels = [level for level in context.get("referenceLevels", []) if isinstance(level, Mapping)]
    events: list[dict[str, Any]] = []

    for level in levels:
        value = _number(level.get("value"))
        if value is None:
            continue
        tolerance = _tolerance(value, stock)
        for index in range(1, len(frame)):
            timestamp = _timestamp(frame.loc[index, "time"])
            if timestamp is None:
                continue
            if not _level_is_available(level, timestamp, market):
                continue
            previous = float(frame.loc[index - 1, "price"])
            current = float(frame.loc[index, "price"])
            crossed_above = previous <= value + tolerance and current > value + tolerance
            crossed_below = previous >= value - tolerance and current < value - tolerance

            if crossed_above:
                events.append(
                    _event(
                        stock=stock,
                        frame=frame,
                        index=index,
                        event_type="cross_above",
                        level=level,
                        tolerance=tolerance,
                        context=context,
                        trigger_bars=1,
                    )
                )
                future = frame.iloc[index + 1 : index + 4]
                positions = future.index[future["price"] < value - tolerance].tolist()
                if positions:
                    reclaim_index = int(positions[0])
                    events.append(
                        _event(
                            stock=stock,
                            frame=frame,
                            index=reclaim_index,
                            event_type="reclaim_below",
                            level=level,
                            tolerance=tolerance,
                            context=context,
                            trigger_bars=reclaim_index - index + 1,
                        )
                    )
                    if reclaim_index == index + 1:
                        events.append(
                            _event(
                                stock=stock,
                                frame=frame,
                                index=reclaim_index,
                                event_type="reject_above",
                                level=level,
                                tolerance=tolerance,
                                context=context,
                                trigger_bars=2,
                            )
                        )
                hold = frame.iloc[index : index + 3]
                if len(hold) == 3 and bool((hold["price"] > value + tolerance).all()):
                    events.append(
                        _event(
                            stock=stock,
                            frame=frame,
                            index=index + 2,
                            event_type="break_and_hold_above",
                            level=level,
                            tolerance=tolerance,
                            context=context,
                            trigger_bars=3,
                        )
                    )

            if crossed_below:
                events.append(
                    _event(
                        stock=stock,
                        frame=frame,
                        index=index,
                        event_type="cross_below",
                        level=level,
                        tolerance=tolerance,
                        context=context,
                        trigger_bars=1,
                    )
                )
                future = frame.iloc[index + 1 : index + 4]
                positions = future.index[future["price"] > value + tolerance].tolist()
                if positions:
                    reclaim_index = int(positions[0])
                    events.append(
                        _event(
                            stock=stock,
                            frame=frame,
                            index=reclaim_index,
                            event_type="reclaim_above",
                            level=level,
                            tolerance=tolerance,
                            context=context,
                            trigger_bars=reclaim_index - index + 1,
                        )
                    )
                    if reclaim_index == index + 1:
                        events.append(
                            _event(
                                stock=stock,
                                frame=frame,
                                index=reclaim_index,
                                event_type="reject_below",
                                level=level,
                                tolerance=tolerance,
                                context=context,
                                trigger_bars=2,
                            )
                        )
                hold = frame.iloc[index : index + 3]
                if len(hold) == 3 and bool((hold["price"] < value - tolerance).all()):
                    events.append(
                        _event(
                            stock=stock,
                            frame=frame,
                            index=index + 2,
                            event_type="break_and_hold_below",
                            level=level,
                            tolerance=tolerance,
                            context=context,
                            trigger_bars=3,
                        )
                    )
    return events


def build_contextual_snapshot(
    stocks: Sequence[Mapping[str, Any]],
    *,
    generated_at: str,
    events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    from trading_research.dashboard.event_study import build_event_studies
    from trading_research.dashboard.intermarket import build_intermarket_observations

    warnings: list[str] = []
    contexts: list[dict[str, Any]] = []
    setup_events: list[dict[str, Any]] = []
    event_studies: list[dict[str, Any]] = []
    intermarket = build_intermarket_observations(stocks)

    for stock in stocks:
        code = str(stock.get("code") or "")
        try:
            data_date = str(stock.get("lastTradeDay") or generated_at)
            context = build_market_context(stock, data_date=data_date)
            context["intermarket"] = intermarket.get(code, [])
            contexts.append(context)
            setup_events.extend(detect_setup_events(stock, context))
            if events:
                event_studies.extend(build_event_studies(stock, events))
        except Exception as exc:
            warnings.append(f"{code or '<unknown>'}: {exc}")

    snapshot = {
        "schemaVersion": CONTEXTUAL_SNAPSHOT_VERSION,
        "generatedAt": generated_at,
        "dataDate": generated_at,
        "quality": {"status": "warning" if warnings else "pass", "warnings": warnings},
        "coverage": {
            "requested": len(stocks),
            "evaluated": len(contexts),
            "skipped": len(stocks) - len(contexts),
        },
        "contexts": contexts,
        "setupEvents": setup_events,
        "eventStudies": event_studies,
        "provenance": {
            "source": "dashboard-generator",
            "definitionVersion": "contextual-research.v1",
        },
    }
    validate_contextual_snapshot(snapshot)
    return snapshot
