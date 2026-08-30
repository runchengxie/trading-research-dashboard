import pytest

from trading_research.dashboard.event_study import build_event_studies


def stock():
    prices = [100.0, 100.5, 101.0, 101.5, 102.0, 101.0, 100.0, 99.0, 98.0]
    times = [
        "2026-08-28 13:00:00",
        "2026-08-28 13:15:00",
        "2026-08-28 13:30:00",
        "2026-08-28 13:45:00",
        "2026-08-28 14:00:00",
        "2026-08-28 14:05:00",
        "2026-08-28 14:15:00",
        "2026-08-28 14:30:00",
        "2026-08-28 15:00:00",
    ]
    return {
        "code": "TEST.US",
        "lastTradeDay": "2026-08-28",
        "intraday": [
            {"time": time, "price": price, "volume": 1000}
            for time, price in zip(times, prices, strict=True)
        ],
    }


def test_event_study_computes_windows_and_reversal():
    studies = build_event_studies(
        stock(),
        [
            {
                "id": "fomc-2026-08-28",
                "category": "FOMC",
                "importance": "high",
                "timestamp": "2026-08-28 14:00:00",
            }
        ],
    )
    study = studies[0]
    metrics = study["metrics"]
    assert study["schemaVersion"] == "trading_research.event_study.v1"
    assert metrics["preReturn"] == pytest.approx(102.0 / 100.0 - 1)
    assert metrics["return15m"] == pytest.approx(100.0 / 102.0 - 1)
    assert metrics["return60m"] == pytest.approx(98.0 / 102.0 - 1)
    assert metrics["mfe60m"] == pytest.approx(0.0)
    assert metrics["mae60m"] == pytest.approx(98.0 / 102.0 - 1)
    assert metrics["initialMoveReversal"] is False


def test_event_study_ignores_other_dates():
    studies = build_event_studies(
        stock(),
        [
            {
                "id": "other-day",
                "category": "CPI",
                "importance": "high",
                "timestamp": "2026-08-27 14:00:00",
            }
        ],
    )
    assert studies == []
