from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PROVENANCE_FIELDS = (
    "source.researchCommit",
    "source.dataPlatformManifest.schemaVersion",
    "source.dataPlatformManifest.generatedAt",
)
_MISSING = object()


def _lookup(snapshot: Mapping[str, Any], dotted_path: str) -> Any:
    value: Any = snapshot
    for part in dotted_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _is_missing(value: Any) -> bool:
    return value is _MISSING or value is None or (
        isinstance(value, str) and not value.strip()
    )


def missing_provenance_fields(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        path for path in PROVENANCE_FIELDS if _is_missing(_lookup(snapshot, path))
    )


def provenance_complete(snapshot: Mapping[str, Any]) -> bool:
    return not missing_provenance_fields(snapshot)


def validate_provenance_consistency(snapshot: Mapping[str, Any]) -> None:
    actual = provenance_complete(snapshot)
    declared = _lookup(snapshot, "quality.checks.provenanceComplete")
    if not isinstance(declared, bool):
        raise ValueError("quality.checks.provenanceComplete must be a boolean")
    if declared != actual:
        raise ValueError(
            "quality.checks.provenanceComplete does not match actual provenance completeness"
        )
    if not actual and _lookup(snapshot, "quality.status") != "warning":
        raise ValueError("quality.status must be warning when provenance is incomplete")
