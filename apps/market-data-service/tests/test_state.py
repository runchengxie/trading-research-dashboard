from datetime import UTC, datetime, timedelta

from market_data_service.contracts import Freshness, Quote
from market_data_service.state import QuoteStore


def test_quote_store_normalizes_keys_and_reports_current_quote() -> None:
    now = datetime(2026, 8, 26, 20, 1, tzinfo=UTC)
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, now - timedelta(seconds=5), "alpaca"))

    state = store.get("us:AAPL", now=now)

    assert state is not None
    assert state.quote.symbol == "us:AAPL"
    assert state.freshness is Freshness.CURRENT


def test_quote_store_reports_stale_and_missing_quotes() -> None:
    now = datetime(2026, 8, 26, 20, 1, tzinfo=UTC)
    store = QuoteStore(max_age_seconds=15)
    store.put(Quote("AAPL.US", 201.25, now - timedelta(seconds=16), "alpaca"))

    state = store.get("AAPL.US", now=now)

    assert state is not None
    assert state.freshness is Freshness.STALE
    assert store.get("MSFT.US", now=now) is None
