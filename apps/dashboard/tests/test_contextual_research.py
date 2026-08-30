import pandas as pd
import pytest

from trading_research.dashboard.contextual_research import (
    build_market_context,
    classify_day_archetype,
    detect_setup_events,
    semantic_reference_levels,
    session_for_timestamp,
)


def daily_rows(count=21, *, start=90.0, step=0.7):
    dates = pd.date_range("2026-08-08", periods=count, freq="D")
    return [
        {
            "date": date.strftime("%Y-%m-%d"),
            "open": start + index * step,
            "high": start + index * step + 0.8,
            "low": start + index * step - 0.8,
            "close": start + index * step + 0.3,
            "volume": 1000,
        }
        for index, date in enumerate(dates)
    ]


def stock_fixture(prices, *, market="US", orb_high=101.0, orb_low=99.0, atr20=2.0):
    times = [
        f"2026-08-28 09:{30 + i * 5:02d}:00"
        for i in range(len(prices))
        if 30 + i * 5 < 60
    ]
    if len(times) < len(prices):
        extra = len(prices) - len(times)
        times += [f"2026-08-28 10:{i * 5:02d}:00" for i in range(extra)]
    return {
        "code": "TEST.US",
        "name": "TEST",
        "market": market,
        "timezone": "America/New_York" if market == "US" else "Asia/Shanghai",
        "lastTradeDay": "2026-08-28",
        "indicators": {
            "lastClose": prices[-1],
            "atr20": atr20,
            "support": 98.0,
            "resistance": 103.0,
            "nearestKeyLevel": 100.0,
            "yesterdayLow": 99.0,
            "yesterdayHigh": 101.0,
            "vwap": 100.0,
            "vwapDev": 0.0,
            "vwapDevThreshold": 1.0,
            "orbHigh": orb_high,
            "orbLow": orb_low,
        },
        "levels": [
            {"type": "support", "value": 98.0, "label": "支撑"},
            {"type": "resistance", "value": 103.0, "label": "阻力"},
        ],
        "daily": [
            {
                "date": "2026-08-26",
                "open": 99.0,
                "high": 100.0,
                "low": 98.0,
                "close": 99.5,
                "volume": 1000,
            },
            {
                "date": "2026-08-27",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1000,
            },
        ],
        "intraday": [
            {"time": time, "price": price, "volume": 1000}
            for time, price in zip(times, prices, strict=True)
        ],
    }


@pytest.mark.parametrize(
    ("timestamp", "market", "timezone", "expected"),
    [
        ("2026-08-28 09:45:00", "US", "America/New_York", "opening_range"),
        ("2026-08-28 10:45:00", "US", "America/New_York", "morning"),
        ("2026-08-28 14:50:00", "CN", "Asia/Shanghai", "close"),
        ("2026-08-28 15:45:00", "HK", "Asia/Hong_Kong", "close"),
    ],
)
def test_session_for_timestamp(timestamp, market, timezone, expected):
    assert session_for_timestamp(timestamp, market, timezone) == expected


def test_semantic_reference_levels_use_only_data_before_intraday_date():
    stock = stock_fixture([100.0, 100.5, 100.2, 100.3, 100.4, 100.5])
    stock["daily"] = daily_rows()
    levels = semantic_reference_levels(stock)
    kinds = {level["kind"] for level in levels}
    assert {
        "previous_day_high",
        "previous_day_low",
        "previous_5d_high",
        "previous_5d_low",
        "opening_range_high",
        "opening_range_low",
        "vwap",
        "support",
        "resistance",
    } <= kinds
    pdh = next(level for level in levels if level["kind"] == "previous_day_high")
    assert pdh["value"] == pytest.approx(104.1)
    assert pdh["distancePct"] == pytest.approx((104.1 - 100.5) / 100.5)


def test_build_market_context_includes_transparent_higher_timeframe_context():
    stock = stock_fixture([100.0, 100.5, 100.8, 101.0, 101.2, 101.4])
    stock["daily"] = daily_rows()
    context = build_market_context(stock, data_date="2026-08-28")
    assert context["higherTimeframe"]["trend20"] == "up"
    assert context["higherTimeframe"]["return20"] > 0.02
    assert 0 <= context["higherTimeframe"]["rangePosition20"] <= 1


def test_classify_opening_drive_up():
    stock = stock_fixture([100.0, 100.6, 101.2, 101.5, 101.8, 102.0], atr20=2.0)
    result = classify_day_archetype(stock)
    assert result["id"] == "opening_drive_up"
    assert result["reasons"]


def test_classify_morning_reversal():
    stock = stock_fixture(
        [100.0, 102.0, 101.5, 100.8, 100.1, 99.8, 99.7, 99.6],
        orb_high=103.0,
        orb_low=98.0,
        atr20=2.0,
    )
    result = classify_day_archetype(stock)
    assert result["id"] == "morning_reversal"


def test_short_intraday_is_insufficient():
    result = classify_day_archetype(stock_fixture([100.0, 100.2, 100.1]))
    assert result["id"] == "insufficient_data"


def test_detect_reclaim_below_uses_prior_day_level_and_forward_outcomes():
    stock = stock_fixture(
        [100.0, 100.4, 101.3, 100.7, 100.5, 100.2, 99.9, 99.7, 99.5],
        orb_high=103.0,
        orb_low=97.0,
        atr20=1.0,
    )
    context = build_market_context(stock, data_date="2026-08-28")
    events = detect_setup_events(stock, context)
    reclaims = [
        event
        for event in events
        if event["eventType"] == "reclaim_below"
        and event["referenceLevel"]["kind"] == "previous_day_high"
    ]
    assert reclaims
    event = reclaims[0]
    assert event["referenceLevel"]["value"] == 101.0
    assert event["timestamp"] == "2026-08-28 09:45:00"
    assert event["outcome"]["return5m"] == pytest.approx(100.5 / 100.7 - 1)
    assert event["outcome"]["mfe30m"] >= event["outcome"]["mae30m"]


def test_orb_and_vwap_do_not_leak_into_early_setup_detection():
    stock = stock_fixture(
        [100.0, 101.4, 100.4, 100.2, 100.1, 100.0, 99.9, 99.8],
        orb_high=101.0,
        orb_low=99.0,
        atr20=1.0,
    )
    context = build_market_context(stock, data_date="2026-08-28")
    events = detect_setup_events(stock, context)
    assert not any(event["referenceLevel"]["kind"] == "vwap" for event in events)
    assert not any(
        event["referenceLevel"]["kind"].startswith("opening_range_")
        and event["timestamp"] < "2026-08-28 10:30:00"
        for event in events
    )


def test_build_market_context_degrades_without_intraday():
    stock = stock_fixture([100.0, 100.2, 100.1])
    stock["intraday"] = None
    context = build_market_context(stock, data_date="2026-08-28")
    assert context["dayArchetype"]["id"] == "insufficient_data"
    assert context["sessions"] == []
    assert context["currentPrice"] == 100.1
    assert context["higherTimeframe"]["trend20"] == "insufficient_data"
