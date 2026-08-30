import pytest

from research_core.contextual import (
    CONDITIONAL_RESEARCH_VERSION,
    validate_conditional_research,
)


def conditional_research():
    return {
        "schemaVersion": CONDITIONAL_RESEARCH_VERSION,
        "generatedAt": "2026-08-30",
        "dateRange": {"start": "2026-08-28", "end": "2026-08-30"},
        "sourceSnapshots": 2,
        "quality": {"status": "pass", "warnings": []},
        "coverage": {
            "requestedSnapshots": 2,
            "evaluatedSnapshots": 2,
            "skippedSnapshots": 0,
            "setupSamples": 2,
            "strategySamples": 2,
        },
        "groups": [
            {
                "dimensions": {
                    "instrument": "TSLA.US",
                    "market": "US",
                    "session": "morning",
                    "dayArchetype": "range",
                    "eventType": "reclaim_below",
                    "referenceLevelKind": "previous_day_high",
                    "strategyId": None,
                    "variantId": None,
                },
                "metrics": {
                    "sampleCount": 2,
                    "winRate": 0.5,
                    "expectancy": 0.005,
                    "meanReturn": 0.005,
                    "meanMfe": 0.02,
                    "meanMae": -0.015,
                    "dateCount": 2,
                    "instrumentCount": 1,
                },
            }
        ],
        "provenance": {
            "source": "contextual-history-summarizer",
            "definitionVersion": "conditional-research.v1",
        },
    }


def test_valid_conditional_research_is_accepted():
    validate_conditional_research(conditional_research())


def test_conditional_research_requires_groups():
    payload = conditional_research()
    del payload["groups"]
    with pytest.raises(ValueError, match="groups"):
        validate_conditional_research(payload)


def test_conditional_research_rejects_invalid_metric_type():
    payload = conditional_research()
    payload["groups"][0]["metrics"]["sampleCount"] = "2"
    with pytest.raises(ValueError, match="sampleCount"):
        validate_conditional_research(payload)
