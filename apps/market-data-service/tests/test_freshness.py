from datetime import UTC, datetime, timedelta

from market_data_service.contracts import Freshness
from market_data_service.freshness import classify_freshness


def test_classify_freshness_uses_explicit_threshold() -> None:
    now = datetime(2026, 8, 26, 3, 0, tzinfo=UTC)
    assert classify_freshness(now - timedelta(seconds=5), now=now, max_age=10) is Freshness.CURRENT
    assert classify_freshness(now - timedelta(seconds=11), now=now, max_age=10) is Freshness.STALE


def test_classify_freshness_marks_future_or_missing_data_unknown() -> None:
    now = datetime(2026, 8, 26, 3, 0, tzinfo=UTC)
    assert classify_freshness(None, now=now, max_age=10) is Freshness.UNKNOWN
    assert classify_freshness(now + timedelta(seconds=1), now=now, max_age=10) is Freshness.UNKNOWN
