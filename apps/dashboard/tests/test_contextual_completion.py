from trading_research.dashboard.contextual_research import (
    build_market_context,
    detect_setup_events,
    session_for_timestamp,
)


def stock():
    daily = []
    for day in range(17, 28):
        daily.append(
            {
                "date": f"2026-08-{day:02d}",
                "open": 100.0 + day,
                "high": 100.0 + day,
                "low": 80.0 + day,
                "close": 90.0 + day,
            }
        )
    return {
        "code": "TEST.US",
        "name": "TEST",
        "market": "US",
        "timezone": "America/New_York",
        "lastTradeDay": "2026-08-28",
        "indicators": {
            "lastClose": 101.0,
            "atr20": 2.0,
            "yesterdayHigh": 999.0,
            "yesterdayLow": 1.0,
            "vwap": None,
            "orbHigh": None,
            "orbLow": None,
        },
        "levels": [],
        "daily": daily,
        "intraday": [
            {"time": "2026-08-28 09:30:00", "price": 100.0, "volume": 100},
            {"time": "2026-08-28 09:35:00", "price": 101.5, "volume": 200},
            {"time": "2026-08-28 09:40:00", "price": 100.5, "volume": 300},
            {"time": "2026-08-28 09:45:00", "price": 100.8, "volume": 400},
        ],
    }


def test_context_includes_previous_week_levels_and_session_observation_fields():
    context = build_market_context(stock(), data_date="2026-08-28")

    levels = {level["kind"]: level["value"] for level in context["referenceLevels"]}
    assert levels["previous_week_high"] == 123.0
    assert levels["previous_week_low"] == 97.0

    session = context["sessions"][0]
    assert session["open"] == 100.0
    assert session["close"] == 100.8
    assert session["volume"] == 1000.0
    assert session["volumeShare"] == 1.0
    assert session["highTimestamp"] == "2026-08-28 09:35:00"
    assert session["lowTimestamp"] == "2026-08-28 09:30:00"
    assert context["features"]["gapPct"] == (100.0 / 117.0) - 1
    assert context["features"]["highTime"] == "2026-08-28 09:35:00"
    assert context["features"]["lowTime"] == "2026-08-28 09:30:00"


def test_session_classification_converts_offset_aware_timestamp_to_local_timezone():
    assert (
        session_for_timestamp(
            "2026-08-28T13:45:00+00:00",
            "US",
            "America/New_York",
        )
        == "opening_range"
    )


def test_setup_event_carries_context_and_trigger_metadata():
    value = stock()
    value["daily"] = [
        {
            "date": f"2026-08-{day:02d}",
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 100.0,
        }
        for day in range(1, 22)
    ]
    value["daily"][-1]["high"] = 101.0
    value["daily"][-1]["low"] = 99.0
    value["indicators"]["yesterdayHigh"] = 101.0
    value["indicators"]["yesterdayLow"] = 99.0
    context = build_market_context(value, data_date="2026-08-28")
    events = detect_setup_events(value, context)

    cross = next(event for event in events if event["eventType"] == "cross_above")
    assert cross["context"]["htfTrend"] == context["higherTimeframe"]["trend20"]
    assert cross["context"]["dayArchetype"] == context["dayArchetype"]["id"]
    assert cross["trigger"]["barCount"] == 1
