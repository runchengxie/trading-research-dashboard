import pytest

from market_data_service.symbols import normalize_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("SZ.300246", "sz300246"), ("sh.600000", "sh600000"), ("sz300246", "sz300246")],
)
def test_normalize_symbol_accepts_common_market_code_forms(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


def test_normalize_symbol_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="symbol"):
        normalize_symbol("300246")
