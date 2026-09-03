from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from research_core import (
    AGENT_RUN_VERSION,
    RESEARCH_EVIDENCE_VERSION,
    validate_agent_run,
    validate_research_evidence,
)

_SELECTION_SCHEMA_VERSION = "1.0.0"
_SELECTION_ARTIFACT_TYPE = "ai_stock_selection"
_SELECTION_METHOD = "llm_candidate_rerank"
_RECEIPT_SCHEMA_VERSION = "1.0.0"
_RECEIPT_ARTIFACT_TYPE = "ai_stock_selection_validation_receipt"
_VALIDATION_PROFILE = "current_full"
_RESPONSE_VERIFICATIONS = {
    "format_only_raw_response_unavailable",
    "byte_exact_evidence",
}
_POINT_IN_TIME_ASSURANCE = {
    "unverified",
    "signal_date_only",
    "externally_timestamped",
    "strict_replay",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def adapt_ai_stock_picker_selection(
    selection_bytes: bytes,
    validation_receipt: Mapping[str, Any],
    *,
    adapted_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project one owner-validated AI Stock Picker selection into canonical records."""

    selection = _load_selection(selection_bytes)
    receipt = _validate_receipt(selection_bytes, selection, validation_receipt)
    adapted_at = _require_string(adapted_at, "adapted_at")

    selection_sha256 = receipt["selection_sha256"]
    run_id = f"ai-stock-picker:{selection_sha256}"
    evidence_id = f"ai-stock-picker-selection:{selection_sha256}"
    artifact_ref = f"artifact://ai-stock-picker/selection/{selection_sha256}"
    limitations = _canonical_limitations(selection, receipt)
    lineage = _require_mapping(selection.get("lineage"), "selection.lineage")
    provenance = {
        "source": "ai-stock-picker",
        "ownerSelectionSchemaVersion": selection["schema_version"],
        "ownerValidationReceiptSchemaVersion": receipt["schema_version"],
        "ownerValidationProfile": receipt["validation_profile"],
        "selectionSha256": selection_sha256,
        "evidenceManifestSha256": receipt.get("evidence_manifest_sha256"),
        "inputSha256": lineage["input_sha256"],
        "candidateSymbolsSha256": lineage["candidate_symbols_sha256"],
        "promptSha256": lineage["prompt_sha256"],
        "responseSha256": lineage["response_sha256"],
        "promptVersion": selection["prompt_version"],
        "selectionMethod": selection["selection_method"],
        "responseSha256Verification": receipt["response_sha256_verification"],
    }

    agent_run: dict[str, Any] = {
        "schemaVersion": AGENT_RUN_VERSION,
        "runId": run_id,
        "status": "completed",
        "completedAt": selection["generated_at"],
        "model": {
            "provider": selection["provider"],
            "name": selection["model"],
        },
        "harness": {"name": "ai-stock-picker"},
        "budget": {},
        "usage": {},
        "tasks": [],
        "artifactRefs": [artifact_ref],
        "evidenceRefs": [evidence_id],
        "limitations": limitations,
        "provenance": provenance,
    }
    evidence: dict[str, Any] = {
        "schemaVersion": RESEARCH_EVIDENCE_VERSION,
        "evidenceId": evidence_id,
        "runId": run_id,
        "evidenceType": "ai_stock_selection",
        "source": {
            "provider": "ai-stock-picker",
            "sourceType": "validated_selection_artifact",
            "method": "owner_validation_receipt",
        },
        "retrievedAt": adapted_at,
        "dataAsOf": selection["data_cutoff"],
        "freshnessStatus": "unknown",
        "verificationStatus": "verified",
        "artifactRef": artifact_ref,
        "contentSha256": selection_sha256,
        "pointInTime": {
            "assurance": selection["point_in_time_assurance"],
            "strict": selection["strict_point_in_time"],
            "eligibleAsOosEvidence": selection["eligible_as_oos_evidence"],
        },
        "limitations": limitations,
        "provenance": provenance,
    }

    validate_agent_run(agent_run)
    validate_research_evidence(evidence)
    return agent_run, evidence


def _load_selection(selection_bytes: bytes) -> dict[str, Any]:
    if not isinstance(selection_bytes, bytes) or not selection_bytes:
        raise ValueError("ai stock picker selection must be non-empty bytes")
    try:
        value = json.loads(selection_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ai stock picker selection must contain valid UTF-8 JSON") from exc
    selection = _require_mapping(value, "selection")
    if selection.get("schema_version") != _SELECTION_SCHEMA_VERSION:
        raise ValueError("unsupported ai stock picker selection schema_version")
    if selection.get("artifact_type") != _SELECTION_ARTIFACT_TYPE:
        raise ValueError("unsupported ai stock picker selection artifact_type")
    if selection.get("selection_method") != _SELECTION_METHOD:
        raise ValueError("unsupported ai stock picker selection_method")

    for field in (
        "market",
        "selection_as_of",
        "generated_at",
        "data_cutoff",
        "provider",
        "model",
        "prompt_version",
    ):
        _require_string(selection.get(field), f"selection.{field}")
    if not isinstance(selection.get("strict_point_in_time"), bool):
        raise ValueError("selection.strict_point_in_time must be a boolean")
    if not isinstance(selection.get("eligible_as_oos_evidence"), bool):
        raise ValueError("selection.eligible_as_oos_evidence must be a boolean")
    assurance = selection.get("point_in_time_assurance")
    if assurance not in _POINT_IN_TIME_ASSURANCE:
        raise ValueError("selection.point_in_time_assurance is unsupported")
    limitations = selection.get("evidence_limitations")
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("selection.evidence_limitations must be a non-empty array")
    _unique_strings(limitations, "selection.evidence_limitations")
    picks = selection.get("picks")
    if not isinstance(picks, list):
        raise ValueError("selection.picks must be an array")

    lineage = _require_mapping(selection.get("lineage"), "selection.lineage")
    for field in (
        "input_sha256",
        "candidate_symbols_sha256",
        "prompt_sha256",
        "response_sha256",
    ):
        _require_sha256(lineage.get(field), f"selection.lineage.{field}")
    return dict(selection)


def _validate_receipt(
    selection_bytes: bytes,
    selection: Mapping[str, Any],
    validation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = _require_mapping(validation_receipt, "validation_receipt")
    if receipt.get("schema_version") != _RECEIPT_SCHEMA_VERSION:
        raise ValueError("unsupported ai stock picker validation receipt schema_version")
    if receipt.get("artifact_type") != _RECEIPT_ARTIFACT_TYPE:
        raise ValueError("unsupported ai stock picker validation receipt artifact_type")
    if receipt.get("valid") is not True:
        raise ValueError("ai stock picker validation receipt must be valid")
    if receipt.get("validation_profile") != _VALIDATION_PROFILE:
        raise ValueError("unsupported ai stock picker validation profile")
    if receipt.get("prompt_hash_revalidated") is not True:
        raise ValueError("ai stock picker prompt hash was not revalidated")
    if receipt.get("commentary_policy_revalidated") is not True:
        raise ValueError("ai stock picker commentary policy was not revalidated")

    selection_sha256 = _require_sha256(
        receipt.get("selection_sha256"), "validation_receipt.selection_sha256"
    )
    if selection_sha256 != hashlib.sha256(selection_bytes).hexdigest():
        raise ValueError("ai stock picker validation receipt does not match selection bytes")
    for receipt_field, selection_field in (
        ("market", "market"),
        ("selection_as_of", "selection_as_of"),
        ("prompt_version", "prompt_version"),
    ):
        if receipt.get(receipt_field) != selection.get(selection_field):
            raise ValueError(
                f"ai stock picker validation receipt {receipt_field} does not match selection"
            )
    if receipt.get("picks") != len(selection["picks"]):
        raise ValueError("ai stock picker validation receipt picks does not match selection")
    response_verification = receipt.get("response_sha256_verification")
    if response_verification not in _RESPONSE_VERIFICATIONS:
        raise ValueError("unsupported ai stock picker response SHA-256 verification")
    evidence_manifest_sha256 = receipt.get("evidence_manifest_sha256")
    if evidence_manifest_sha256 is not None:
        _require_sha256(
            evidence_manifest_sha256,
            "validation_receipt.evidence_manifest_sha256",
        )
    return dict(receipt)


def _canonical_limitations(
    selection: Mapping[str, Any], receipt: Mapping[str, Any]
) -> list[str]:
    limitations = list(selection["evidence_limitations"])
    if receipt["response_sha256_verification"] != "byte_exact_evidence":
        limitations.append("provider_response_not_byte_exact_revalidated")
    return list(dict.fromkeys(limitations))


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _unique_strings(value: list[Any], label: str) -> list[str]:
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    return value
