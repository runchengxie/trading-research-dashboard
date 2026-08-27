from datetime import UTC, datetime

import pytest

import market_data_service.contracts as contracts
from market_data_service.contracts import Quote, QuoteStatus


def test_quote_normalizes_symbol_and_exposes_source_metadata() -> None:
    quote = Quote(
        symbol="SZ.300246",
        price=12.34,
        timestamp=datetime(2026, 8, 26, 2, 30, tzinfo=UTC),
        source="fake",
    )

    assert quote.symbol == "sz300246"
    assert quote.status is QuoteStatus.LIVE
    assert quote.source == "fake"


def test_quote_rejects_naive_timestamp_and_non_positive_price() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Quote("sz300246", 12.34, datetime(2026, 8, 26, 2, 30), "fake")

    with pytest.raises(ValueError, match="price"):
        Quote("sz300246", 0, datetime.now(UTC), "fake")


def test_historical_bar_contract_is_exposed() -> None:
    assert hasattr(contracts, "Bar")
    assert hasattr(contracts, "BarTimeframe")
