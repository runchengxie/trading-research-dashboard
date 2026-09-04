import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_runtime_candidate import validate_runtime_candidate


def _snapshot(*, generated_at="2026-08-27", codes=("sz300246",), trade_day="2026-08-26"):
    return {
        "generatedAt": generated_at,
        "stocks": [
            {
                "code": code,
                "lastTradeDay": trade_day,
                "daily": [{"date": trade_day, "close": 10.0}],
            }
            for code in codes
        ],
    }


def test_runtime_candidate_accepts_same_or_newer_complete_snapshot() -> None:
    baseline = _snapshot(
        generated_at="2026-08-26",
        codes=("sz300246", "510050.SH"),
        trade_day="2026-08-25",
    )
    candidate = _snapshot(
        generated_at="2026-08-27",
        codes=("sz300246", "510050.SH"),
        trade_day="2026-08-26",
    )

    validate_runtime_candidate(candidate, baseline)


def test_shadow_runtime_candidate_allows_missing_baseline_instrument() -> None:
    baseline = _snapshot(
        generated_at="2026-08-26",
        codes=("sz300246", "TSLA.US"),
        trade_day="2026-08-25",
    )
    candidate = _snapshot(
        generated_at="2026-08-27",
        codes=("sz300246",),
        trade_day="2026-08-26",
    )

    validate_runtime_candidate(candidate, baseline, mode="shadow")


@pytest.mark.parametrize(
    ("candidate", "message"),
    [
        ({"generatedAt": "2026-08-27", "stocks": []}, "stocks"),
        (_snapshot(generated_at="2026-08-25"), "generatedAt"),
        (_snapshot(codes=("510050.SH",)), "sz300246"),
        (_snapshot(trade_day="2026-08-24"), "lastTradeDay"),
    ],
)
def test_runtime_candidate_rejects_regressions(candidate: dict, message: str) -> None:
    baseline = _snapshot(generated_at="2026-08-26", trade_day="2026-08-25")

    with pytest.raises(ValueError, match=message):
        validate_runtime_candidate(candidate, baseline)
