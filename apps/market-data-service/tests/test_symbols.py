import pytest

from market_data_service.symbols import Market, normalize_symbol, parse_instrument


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SZ.300246", "sz300246"),
        ("sh.600000", "sh600000"),
        ("sz300246", "sz300246"),
        ("300246.SZ", "sz300246"),
        ("00700.HK", "hk00700"),
        ("HK.00700", "hk00700"),
        ("hk00700", "hk00700"),
        ("AAPL.US", "us:AAPL"),
        ("us:AAPL", "us:AAPL"),
    ],
)
def test_normalize_symbol_accepts_cross_market_forms(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


def test_parse_instrument_exposes_market_provider_and_currency_metadata() -> None:
    cn = parse_instrument("300246.SZ")
    hk = parse_instrument("00700.HK")
    us = parse_instrument("AAPL.US")

    assert (cn.market, cn.provider_symbol, cn.currency, cn.timezone) == (
        Market.CN,
        "300246",
        "CNY",
        "Asia/Shanghai",
    )
    assert (hk.market, hk.provider_symbol, hk.currency, hk.timezone) == (
        Market.HK,
        "00700",
        "HKD",
        "Asia/Hong_Kong",
    )
    assert (us.market, us.provider_symbol, us.currency, us.timezone) == (
        Market.US,
        "AAPL",
        "USD",
        "America/New_York",
    )


def test_parse_instrument_accepts_bare_us_ticker_only_with_explicit_market() -> None:
    instrument = parse_instrument("AAPL", market=Market.US)
    assert instrument.symbol == "us:AAPL"

    with pytest.raises(ValueError, match="symbol"):
        normalize_symbol("AAPL")


def test_normalize_symbol_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="symbol"):
        normalize_symbol("300246")
