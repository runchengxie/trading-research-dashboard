import pandas as pd
import pytest

from niu_men_line_strategy.oos_support import (
    attach_membership,
    dates,
    parse_reset_bars_neighborhood,
)


def test_dates_parses_compact_trade_dates() -> None:
    result = dates(pd.Series(["20260827"]), errors="raise")
    assert result.iloc[0] == pd.Timestamp("2026-08-27")


def test_parse_reset_bars_neighborhood_deduplicates_and_sorts() -> None:
    assert parse_reset_bars_neighborhood("5,3,5") == (3, 5)


def test_parse_reset_bars_neighborhood_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        parse_reset_bars_neighborhood("0,3")


def test_attach_membership_respects_effective_and_end_dates() -> None:
    data = pd.DataFrame(index=pd.to_datetime(["2026-01-02", "2026-01-05"]))
    memberships = pd.DataFrame(
        {
            "effective_date": pd.to_datetime(["2026-01-01"]),
            "end_date": pd.to_datetime(["2026-01-03"]),
            "mapped_industry_code": ["I1"],
        }
    )

    result = attach_membership(data, memberships)

    assert result["industry_code"].iloc[0] == "I1"
    assert pd.isna(result["industry_code"].iloc[1])
