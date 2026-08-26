"""Validate Dashboard research snapshots against the canonical JSON Schema."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "research-snapshot.schema.json"
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Raise ValueError when snapshot does not satisfy the canonical schema."""

    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot schema validation failed: root must be an object")

    errors = sorted(
        _VALIDATOR.iter_errors(snapshot),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(
            f"snapshot schema validation failed at {_error_location(error)}: {error.message}"
        )


def load_snapshot(path: Path) -> dict[str, Any]:
    """Read UTF-8 JSON, validate it, and return the object."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"snapshot schema validation failed: invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise TypeError("snapshot schema validation failed: root must be an object")
    validate_snapshot(payload)
    return payload
