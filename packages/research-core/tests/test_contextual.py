import json
from importlib.resources import files

import pytest
from jsonschema import Draft202012Validator

from research_core.contextual import (
    CONTEXTUAL_SNAPSHOT_VERSION,
    EVENT_STUDY_VERSION,
    MARKET_CONTEXT_VERSION,
    SETUP_EVENT_VERSION,
    load_contextual_snapshot,
    validate_contextual_snapshot,
    validate_event_study,
    validate_market_context,
    validate_setup_event,
)


def market_context():
    return {
        "schemaVersion": MARKET_CONTEXT_VERSION,
        "instrument": {"code": "TSLA.US", "name": "TSLA"},
        "dataDate": "2026-08-28",
        "market": "US",
        "timezone": "America/New_York",
        "currentPrice": 220.0,
        "referenceLevels": [
            {
                "kind": "previous_day_high",
                "value": 221.0,
                "distancePct": 1 / 220,
                "sourceLabel": "前一日高点",
            }
        ],
        "sessions": [
            {
                "id": "opening_range",
                "high": 221.0,
                "low": 218.0,
                "returnPct": 0.005,
                "bars": 12,
            }
        ],
        "higherTimeframe": {
            "trend20": "up",
            "return20": 0.08,
            "rangePosition20": 0.82,
        },
        "dayArchetype": {"id": "range", "reasons": ["日内区间未达到趋势阈值"]},
        "features": {
            "rangeToAtr": 0.8,
            "closeLocation": 0.5,
            "intradayRangePct": 0.014,
        },
        "intermarket": [],
        "provenance": {
            "source": "dashboard-data-json",
            "definitionVersion": "market-context.v1",
        },
    }


def setup_event():
    return {
        "schemaVersion": SETUP_EVENT_VERSION,
        "instrument": "TSLA.US",
        "dataDate": "2026-08-28",
        "timestamp": "2026-08-28 10:05:00",
        "session": "opening_range",
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
            "return30m": -0.003,
            "mfe30m": 0.001,
            "mae30m": -0.005,
        },
        "definitionVersion": "setup-detector.v1",
        "provenance": {"source": "dashboard-data-json"},
    }


def event_study():
    return {
        "schemaVersion": EVENT_STUDY_VERSION,
        "event": {
            "id": "fomc-2026-07-29",
            "category": "FOMC",
            "importance": "high",
            "timestamp": "2026-07-29 14:00:00",
        },
        "instrument": "TSLA.US",
        "dataDate": "2026-07-29",
        "preWindowMinutes": 60,
        "postWindowMinutes": 60,
        "metrics": {
            "preReturn": 0.001,
            "preRangePct": 0.004,
            "immediateRangePct": 0.006,
            "return15m": -0.002,
            "return30m": 0.001,
            "return60m": 0.003,
            "mfe60m": 0.008,
            "mae60m": -0.004,
            "initialMoveReversal": True,
        },
        "provenance": {
            "source": "provided-event-input",
            "definitionVersion": "event-study.v1",
        },
    }


def contextual_snapshot():
    return {
        "schemaVersion": CONTEXTUAL_SNAPSHOT_VERSION,
        "generatedAt": "2026-08-28",
        "dataDate": "2026-08-28",
        "quality": {"status": "pass", "warnings": []},
        "coverage": {"requested": 1, "evaluated": 1, "skipped": 0},
        "contexts": [market_context()],
        "setupEvents": [setup_event()],
        "eventStudies": [],
        "provenance": {
            "source": "dashboard-generator",
            "definitionVersion": "contextual-research.v1",
        },
    }


def test_contextual_contract_versions_are_stable():
    assert MARKET_CONTEXT_VERSION == "trading_research.market_context.v1"
    assert SETUP_EVENT_VERSION == "trading_research.setup_event.v1"
    assert EVENT_STUDY_VERSION == "trading_research.event_study.v1"
    assert CONTEXTUAL_SNAPSHOT_VERSION == "trading_research.contextual_snapshot.v1"


def test_valid_contracts_are_accepted():
    validate_market_context(market_context())
    validate_setup_event(setup_event())
    validate_event_study(event_study())
    validate_contextual_snapshot(contextual_snapshot())


def test_market_context_requires_instrument():
    payload = market_context()
    del payload["instrument"]
    with pytest.raises(ValueError, match="instrument"):
        validate_market_context(payload)


def test_contextual_snapshot_validates_nested_events():
    payload = contextual_snapshot()
    del payload["setupEvents"][0]["eventType"]
    with pytest.raises(ValueError, match="eventType"):
        validate_contextual_snapshot(payload)


def test_contextual_snapshot_schema_validates_nested_contexts_standalone():
    schema = json.loads(
        files("research_core.schemas")
        .joinpath("contextual-snapshot.v1.schema.json")
        .read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)

    valid_errors = list(validator.iter_errors(contextual_snapshot()))
    assert valid_errors == []

    malformed = contextual_snapshot()
    malformed["contexts"] = [{}]
    errors = list(validator.iter_errors(malformed))
    assert any("instrument" in error.message for error in errors)


def test_load_contextual_snapshot(tmp_path):
    path = tmp_path / "contextual.json"
    path.write_text(json.dumps(contextual_snapshot()), encoding="utf-8")
    assert load_contextual_snapshot(path)["coverage"]["evaluated"] == 1
