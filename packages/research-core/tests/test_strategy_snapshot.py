import json
from pathlib import Path

import pytest

from research_core.adapters import adapt_niu_men_v2
from research_core.strategy_snapshot import (
    STRATEGY_SNAPSHOT_VERSION,
    validate_strategy_snapshot,
)

RESEARCH_CORE = Path(__file__).resolve().parents[1]
V2_FIXTURES = RESEARCH_CORE / "tests" / "fixtures" / "research_snapshot"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def valid_v2() -> dict:
    return read_json(V2_FIXTURES / "valid_v2.json")


def test_version_constant_is_v1() -> None:
    assert STRATEGY_SNAPSHOT_VERSION == "trading_research.strategy_snapshot.v1"


def test_adapted_niu_men_v2_validates_against_generic_schema() -> None:
    envelope = adapt_niu_men_v2(valid_v2())
    validate_strategy_snapshot(envelope)


def test_adapter_promotes_identity_times_and_quality() -> None:
    snapshot = valid_v2()
    envelope = adapt_niu_men_v2(snapshot)
    assert envelope["schemaVersion"] == "trading_research.strategy_snapshot.v1"
    assert envelope["strategy"] == {"id": "niu-men-line", "label": "牛门线"}
    assert envelope["generatedAt"] == snapshot["generatedAt"]
    assert envelope["dataDate"] == snapshot["source"]["dataDate"]
    assert envelope["quality"]["status"] == snapshot["quality"]["status"]
    assert (
        envelope["quality"]["checks"]["provenanceComplete"]
        == snapshot["quality"]["checks"]["provenanceComplete"]
    )


def test_adapter_promotes_coverage_and_provenance() -> None:
    snapshot = valid_v2()
    envelope = adapt_niu_men_v2(snapshot)
    assert envelope["coverage"] == {
        "requested": snapshot["coverage"]["requestedSymbols"],
        "evaluated": snapshot["coverage"]["evaluatedSymbols"],
        "skipped": snapshot["coverage"]["skippedSymbols"],
    }
    provenance = envelope["provenance"]
    source = snapshot["source"]
    manifest = source["dataPlatformManifest"]
    assert provenance == {
        "researchCommit": source["researchCommit"],
        "dataPlatform": source["dataPlatform"],
        "dataPlatformSchemaVersion": manifest["schemaVersion"],
        "dataPlatformGeneratedAt": manifest["generatedAt"],
        "oosSchemaVersion": source["oosSchemaVersion"],
        "oosGeneratedAt": source["oosGeneratedAt"],
    }


def test_adapter_promotes_variant_metrics_exactly() -> None:
    snapshot = valid_v2()
    envelope = adapt_niu_men_v2(snapshot)
    original = snapshot["variants"][0]
    adapted = envelope["variants"][0]
    metric_keys = [key for key in original if key not in ("id", "label", "symbols", "foldRows")]
    assert set(adapted["metrics"]) == set(metric_keys)
    for key in metric_keys:
        assert adapted["metrics"][key] == original[key]
    assert adapted["symbols"] == original["symbols"]
    assert adapted["foldRows"] == original["foldRows"]
    assert len(envelope["variants"]) == len(snapshot["variants"])


def test_adapter_promotes_walk_forward_and_timing() -> None:
    snapshot = valid_v2()
    envelope = adapt_niu_men_v2(snapshot)
    walk_forward = envelope["walkForward"]
    original = snapshot["walkForward"]
    assert walk_forward["trainBars"] == original["trainBars"]
    assert walk_forward["testBars"] == original["testBars"]
    assert walk_forward["stepBars"] == original["stepBars"]
    assert walk_forward["semantics"] == original["foldSemantics"]
    assert len(walk_forward["summaries"]) == len(original["summaries"])
    first = original["summaries"][0]
    adapted_summary = walk_forward["summaries"][0]
    assert adapted_summary["variant"] == first["variant"]
    assert adapted_summary["metrics"]["annualizedReturnMedian"] == first["annualizedReturnMedian"]
    assert envelope["executionTiming"] == snapshot["executionConstraints"]["timing"]


def test_adapter_keeps_source_payload_for_strategy_rendering() -> None:
    snapshot = valid_v2()
    envelope = adapt_niu_men_v2(snapshot)
    assert envelope["source"]["wireVersion"] == "niu_men.research_snapshot.v2"
    assert envelope["source"]["payload"] == snapshot
    assert "details" not in envelope


def test_unsupported_generic_version_is_rejected() -> None:
    envelope = adapt_niu_men_v2(valid_v2())
    envelope["schemaVersion"] = "trading_research.strategy_snapshot.v9"
    with pytest.raises(ValueError, match="schemaVersion"):
        validate_strategy_snapshot(envelope)


def test_non_mapping_envelope_is_rejected() -> None:
    with pytest.raises(TypeError, match="root must be an object"):
        validate_strategy_snapshot([])  # type: ignore[arg-type]


def test_committed_generic_fixture_matches_current_adapter() -> None:
    """The committed envelope is exactly what the current adapter produces."""

    fixture = read_json(RESEARCH_CORE / "tests" / "fixtures" / "strategy_snapshot" / "niu_men_generic_v1.json")
    assert fixture == adapt_niu_men_v2(valid_v2())


def test_rbreaker_sample_fixture_validates() -> None:
    fixture = read_json(RESEARCH_CORE / "tests" / "fixtures" / "strategy_snapshot" / "rbreaker_sample_v1.json")
    validate_strategy_snapshot(fixture)
    assert fixture["strategy"]["id"] == "r-breaker"


def test_strategy_snapshot_accepts_execution_capabilities() -> None:
    fixture = read_json(RESEARCH_CORE / "tests" / "fixtures" / "strategy_snapshot" / "rbreaker_sample_v1.json")
    fixture["variants"][0]["executionCapabilities"] = {
        "blockedEntry": "not_modelled",
        "blockedExitDay": "not_modelled",
    }

    validate_strategy_snapshot(fixture)
