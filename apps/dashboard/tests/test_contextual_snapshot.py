from research_core import validate_contextual_snapshot
from trading_research.dashboard.contextual_research import build_contextual_snapshot


def stock(code="TEST.US", *, last_trade_day="2026-08-28"):
    daily = []
    for index in range(21):
        close = 100.0 + index * 0.2
        daily.append(
            {
                "date": f"2026-08-{8 + index:02d}",
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1000,
            }
        )
    return {
        "code": code,
        "name": code,
        "market": "US",
        "timezone": "America/New_York",
        "lastTradeDay": last_trade_day,
        "indicators": {
            "lastClose": 104.0,
            "atr20": 2.0,
            "support": 100.0,
            "resistance": 106.0,
            "nearestKeyLevel": 104.0,
            "yesterdayLow": 102.0,
            "yesterdayHigh": 105.0,
            "vwap": 104.0,
            "vwapDev": 0.0,
            "vwapDevThreshold": 1.0,
            "orbHigh": 104.5,
            "orbLow": 103.5,
        },
        "levels": [],
        "daily": daily,
        "intraday": [
            {
                "time": f"{last_trade_day} 09:{30 + i * 5:02d}:00",
                "price": 103.8 + i * 0.1,
                "volume": 1000,
            }
            for i in range(6)
        ],
    }


def test_build_contextual_snapshot_validates_and_reports_coverage():
    snapshot = build_contextual_snapshot(
        [stock("ONE.US"), stock("TWO.US")],
        generated_at="2026-08-28",
    )
    validate_contextual_snapshot(snapshot)
    assert snapshot["schemaVersion"] == "trading_research.contextual_snapshot.v1"
    assert snapshot["coverage"] == {"requested": 2, "evaluated": 2, "skipped": 0}
    assert len(snapshot["contexts"]) == 2
    assert snapshot["quality"]["status"] == "pass"


def test_context_uses_each_instruments_own_last_trade_day():
    snapshot = build_contextual_snapshot(
        [
            stock("ONE.US", last_trade_day="2026-08-28"),
            stock("TWO.US", last_trade_day="2026-08-27"),
        ],
        generated_at="2026-08-28",
    )
    assert [context["dataDate"] for context in snapshot["contexts"]] == [
        "2026-08-28",
        "2026-08-27",
    ]
