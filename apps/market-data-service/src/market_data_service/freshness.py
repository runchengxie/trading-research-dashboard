from __future__ import annotations

from datetime import datetime, timedelta

from .contracts import Freshness


def classify_freshness(
    timestamp: datetime | None,
    *,
    now: datetime,
    max_age: float,
) -> Freshness:
    if timestamp is None or timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return Freshness.UNKNOWN
    if timestamp > now:
        return Freshness.UNKNOWN
    return Freshness.CURRENT if now - timestamp <= timedelta(seconds=max_age) else Freshness.STALE
