from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "niu_men.research_snapshot.v2"
_SCHEMA_RESOURCE = files("research_core.schemas").joinpath("research-snapshot.schema.json")
_SCHEMA = json.loads(_SCHEMA_RESOURCE.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
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


def load_snapshot(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"snapshot schema validation failed: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TypeError("snapshot schema validation failed: root must be an object")
    validate_snapshot(payload)
    return payload
