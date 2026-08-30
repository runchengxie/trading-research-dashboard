import pytest

from trading_research.dashboard.contextual_history import aggregate_contextual_history


def snapshot(data_date, *, archetype, return_30m, mfe, mae):
    return {
        "schemaVersion": "trading_research.contextual_snapshot.v1",
        "generatedAt": f"{data_date}T18:00:00Z",
        "dataDate": data_date,
        "quality": {"status": "pass", "warnings": []},
        "coverage": {"requested": 1, "evaluated": 1, "skipped": 0},
        "contexts": [
            {
                "schemaVersion": "trading_research.market_context.v1",
                "instrument": {"code": "TSLA.US", "name": "TSLA"},
                "dataDate": data_date,
                "market": "US",
                "timezone": "America/New_York",
                "currentPrice": 220.0,
                "referenceLevels": [],
                "sessions": [],
                "higherTimeframe": {
                    "trend20": "up",
                    "return20": 0.08,
                    "rangePosition20": 0.8,
                },
                "dayArchetype": {"id": archetype, "reasons": ["fixture"]},
                "features": {
                    "rangeToAtr": 1.0,
                    "closeLocation": 0.7,
                    "intradayRangePct": 0.02,
                },
                "intermarket": [],
                "provenance": {
                    "source": "fixture",
                    "definitionVersion": "market-context.v1",
                },
            }
        ],
        "setupEvents": [
            {
                "schemaVersion": "trading_research.setup_event.v1",
                "instrument": "TSLA.US",
                "dataDate": data_date,
                "timestamp": f"{data_date} 10:45:00",
                "session": "morning",
                "eventType": "reclaim_below",
                "referenceLevel": {
                    "kind": "previous_day_high",
                    "value": 221.0,
                    "sourceLabel": "前一日高点",
                },
                "observedPrice": 220.8,
                "tolerance": 0.11,
                "outcome": {
                    "return5m": -0.001,
                    "return15m": -0.002,
                    "return30m": return_30m,
                    "mfe30m": mfe,
                    "mae30m": mae,
                },
                "definitionVersion": "setup-detector.v1",
                "provenance": {"source": "fixture"},
            }
        ],
        "eventStudies": [],
        "provenance": {
            "source": "fixture",
            "definitionVersion": "contextual-research.v1",
        },
    }


def test_aggregates_setup_outcomes_by_contextual_dimensions():
    result = aggregate_contextual_history(
        [
            snapshot("2026-08-28", archetype="range", return_30m=0.02, mfe=0.03, mae=-0.01),
            snapshot("2026-08-29", archetype="range", return_30m=-0.01, mfe=0.01, mae=-0.02),
        ],
        generated_at="2026-08-30",
    )

    group = next(
        group
        for group in result["groups"]
        if group["dimensions"]["eventType"] == "reclaim_below"
    )
    assert group["dimensions"]["dayArchetype"] == "range"
    assert group["metrics"] == {
        "sampleCount": 2,
        "winRate": pytest.approx(0.5),
        "expectancy": pytest.approx(0.005),
        "meanReturn": pytest.approx(0.005),
        "meanMfe": pytest.approx(0.02),
        "meanMae": pytest.approx(-0.015),
        "dateCount": 2,
        "instrumentCount": 1,
    }


def test_aggregates_strategy_outcomes_without_inventing_missing_metrics():
    result = aggregate_contextual_history(
        [snapshot("2026-08-28", archetype="range", return_30m=0.02, mfe=0.03, mae=-0.01)],
        generated_at="2026-08-30",
        strategy_outcomes=[
            {
                "strategyId": "r-breaker",
                "variantId": "default",
                "instrument": "TSLA.US",
                "dataDate": "2026-08-28",
                "session": "morning",
                "eventType": "reclaim_below",
                "referenceLevelKind": "previous_day_high",
                "return": 0.01,
                "mfe": 0.02,
                "mae": -0.01,
                "rMultiple": 1.0,
            },
            {
                "strategyId": "r-breaker",
                "variantId": "default",
                "instrument": "TSLA.US",
                "dataDate": "2026-08-28",
                "session": "morning",
                "eventType": "reclaim_below",
                "referenceLevelKind": "previous_day_high",
                "return": -0.03,
                "mfe": 0.01,
                "mae": -0.04,
            },
        ],
    )

    group = next(
        group
        for group in result["groups"]
        if group["dimensions"]["strategyId"] == "r-breaker"
    )
    assert group["metrics"]["sampleCount"] == 2
    assert group["metrics"]["winRate"] == pytest.approx(0.5)
    assert group["metrics"]["expectancy"] == pytest.approx(-0.01)
    assert group["metrics"]["meanMfe"] == pytest.approx(0.015)
    assert group["metrics"]["meanMae"] == pytest.approx(-0.025)
    assert result["coverage"]["strategySamples"] == 2
