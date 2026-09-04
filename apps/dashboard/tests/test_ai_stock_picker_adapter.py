from __future__ import annotations

import hashlib
import json

import pytest
from research_core import validate_agent_run, validate_research_evidence

from trading_research.ai_stock_picker_adapter import adapt_ai_stock_picker_selection


def _selection_bytes() -> bytes:
    payload = {
        "schema_version": "1.0.0",
        "artifact_type": "ai_stock_selection",
        "market": "CN",
        "selection_as_of": "2026-07-15",
        "candidate_observation_date": "2026-07-14",
        "candidate_generated_at": "2026-07-14T14:00:00Z",
        "data_cutoff": "2026-07-14",
        "upstream_execution_not_before": "next_trading_session",
        "generated_at": "2026-07-15T02:00:00Z",
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "prompt_version": "2026-07-29.1",
        "style": "momentum",
        "input_contract": "hot_sector_candidate_universe_v1",
        "temporal_status": "contemporaneous",
        "point_in_time_assurance": "signal_date_only",
        "strict_point_in_time": False,
        "eligible_as_oos_evidence": False,
        "evidence_limitations": [
            "rotation_publisher_receipt_unavailable",
            "candidate_artifact_does_not_establish_out_of_sample_validity",
        ],
        "input_count": 20,
        "requested_top_n": 1,
        "selection_method": "llm_candidate_rerank",
        "lineage": {
            "candidate_path": "/producer-owned/candidates.json",
            "input_sha256": "1" * 64,
            "candidate_symbols_sha256": "2" * 64,
            "prompt_sha256": "3" * 64,
            "response_sha256": "4" * 64,
        },
        "picks": [
            {
                "rank": 1,
                "symbol": "600000.SH",
                "name": "浦发银行",
                "topic": "银行",
                "confidence_score": 8,
                "reasoning": "依据 score=8.1 候选字段进行相对排序",
                "risk_note": "仅依据 score=8.1，风险解读仍有信息边界",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _receipt(selection_bytes: bytes) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "ai_stock_selection_validation_receipt",
        "valid": True,
        "market": "CN",
        "selection_sha256": hashlib.sha256(selection_bytes).hexdigest(),
        "selection_as_of": "2026-07-15",
        "prompt_version": "2026-07-29.1",
        "picks": 1,
        "validation_profile": "current_full",
        "prompt_hash_revalidated": True,
        "commentary_policy_revalidated": True,
        "response_sha256_verification": "format_only_raw_response_unavailable",
        "evidence_manifest_sha256": None,
    }


def _mutate_selection(**updates: object) -> bytes:
    payload = json.loads(_selection_bytes())
    payload.update(updates)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def test_adapts_owner_validated_selection_to_canonical_records() -> None:
    selection_bytes = _selection_bytes()

    agent_run, evidence = adapt_ai_stock_picker_selection(
        selection_bytes,
        _receipt(selection_bytes),
        adapted_at="2026-09-03T09:15:00Z",
    )

    validate_agent_run(agent_run)
    validate_research_evidence(evidence)

    selection_sha = hashlib.sha256(selection_bytes).hexdigest()
    assert agent_run["runId"] == f"ai-stock-picker:{selection_sha}"
    assert agent_run["status"] == "completed"
    assert "startedAt" not in agent_run
    assert agent_run["completedAt"] == "2026-07-15T02:00:00Z"
    assert agent_run["model"] == {
        "provider": "deepseek",
        "name": "deepseek-v4-flash",
    }
    assert agent_run["harness"] == {"name": "ai-stock-picker"}
    assert agent_run["budget"] == {}
    assert agent_run["usage"] == {}
    assert agent_run["tasks"] == []

    assert evidence["evidenceId"] == f"ai-stock-picker-selection:{selection_sha}"
    assert evidence["runId"] == agent_run["runId"]
    assert evidence["retrievedAt"] == "2026-09-03T09:15:00Z"
    assert evidence["dataAsOf"] == "2026-07-14"
    assert evidence["contentSha256"] == selection_sha
    assert evidence["pointInTime"] == {
        "assurance": "signal_date_only",
        "strict": False,
        "eligibleAsOosEvidence": False,
    }
    assert "provider_response_not_byte_exact_revalidated" in evidence["limitations"]


def test_byte_exact_receipt_requires_evidence_manifest_digest() -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt["response_sha256_verification"] = "byte_exact_evidence"

    with pytest.raises(ValueError, match="evidence manifest"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_format_only_receipt_rejects_evidence_manifest_digest() -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt["evidence_manifest_sha256"] = "5" * 64

    with pytest.raises(ValueError, match="evidence manifest"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_byte_exact_receipt_preserves_stronger_evidence() -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt["response_sha256_verification"] = "byte_exact_evidence"
    receipt["evidence_manifest_sha256"] = "5" * 64

    agent_run, evidence = adapt_ai_stock_picker_selection(
        selection_bytes,
        receipt,
        adapted_at="2026-09-03T09:15:00Z",
    )

    assert "provider_response_not_byte_exact_revalidated" not in evidence["limitations"]
    assert agent_run["provenance"]["evidenceManifestSha256"] == "5" * 64
    assert evidence["provenance"]["evidenceManifestSha256"] == "5" * 64


def test_returned_canonical_records_do_not_share_mutable_state() -> None:
    selection_bytes = _selection_bytes()
    agent_run, evidence = adapt_ai_stock_picker_selection(
        selection_bytes,
        _receipt(selection_bytes),
        adapted_at="2026-09-03T09:15:00Z",
    )
    original_selection_sha = evidence["provenance"]["selectionSha256"]

    agent_run["limitations"].append("consumer-local-mutation")
    agent_run["provenance"]["selectionSha256"] = "0" * 64

    assert "consumer-local-mutation" not in evidence["limitations"]
    assert evidence["provenance"]["selectionSha256"] == original_selection_sha


def test_rejects_receipt_bound_to_different_selection_bytes() -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt["selection_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="does not match selection bytes"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("valid", False, "must be valid"),
        ("validation_profile", "legacy_read_only", "validation profile"),
        ("prompt_hash_revalidated", False, "prompt hash"),
        ("commentary_policy_revalidated", False, "commentary policy"),
    ],
)
def test_rejects_receipt_without_current_owner_validation(
    field: str, value: object, message: str
) -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt[field] = value

    with pytest.raises(ValueError, match=message):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("market", "US"),
        ("selection_as_of", "2026-07-16"),
        ("prompt_version", "2026-07-15.3"),
        ("picks", 2),
    ],
)
def test_rejects_receipt_identity_mismatch(field: str, value: object) -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt[field] = value

    with pytest.raises(ValueError, match=field):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2.0.0", "schema_version"),
        ("artifact_type", "other", "artifact_type"),
        ("selection_method", "free_form", "selection_method"),
    ],
)
def test_rejects_unsupported_selection_contract(
    field: str, value: object, message: str
) -> None:
    selection_bytes = _mutate_selection(**{field: value})

    with pytest.raises(ValueError, match=message):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            _receipt(selection_bytes),
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_rejects_malformed_selection_lineage_digest() -> None:
    payload = json.loads(_selection_bytes())
    payload["lineage"]["prompt_sha256"] = "not-a-digest"
    selection_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")

    with pytest.raises(ValueError, match="prompt_sha256"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            _receipt(selection_bytes),
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_rejects_malformed_evidence_manifest_digest() -> None:
    selection_bytes = _selection_bytes()
    receipt = _receipt(selection_bytes)
    receipt["response_sha256_verification"] = "byte_exact_evidence"
    receipt["evidence_manifest_sha256"] = "not-a-digest"

    with pytest.raises(ValueError, match="evidence_manifest_sha256"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            receipt,
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_rejects_unbound_legacy_validation_summary() -> None:
    selection_bytes = _selection_bytes()
    summary = {
        "valid": True,
        "market": "CN",
        "prompt_version": "2026-07-29.1",
    }

    with pytest.raises(ValueError, match="schema_version"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            summary,
            adapted_at="2026-09-03T09:15:00Z",
        )


def test_requires_explicit_non_empty_adapted_at() -> None:
    selection_bytes = _selection_bytes()

    with pytest.raises(ValueError, match="adapted_at"):
        adapt_ai_stock_picker_selection(
            selection_bytes,
            _receipt(selection_bytes),
            adapted_at="",
        )
