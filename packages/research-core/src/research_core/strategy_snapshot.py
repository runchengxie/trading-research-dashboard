from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

STRATEGY_SNAPSHOT_VERSION = "trading_research.strategy_snapshot.v1"
_SCHEMA_RESOURCE = files("research_core.schemas").joinpath(
    "strategy-snapshot.v1.schema.json"
)
_SCHEMA = json.loads(_SCHEMA_RESOURCE.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def validate_strategy_snapshot(envelope: Mapping[str, Any]) -> None:
    """Raise TypeError/ValueError when the envelope violates the v1 contract."""

    if not isinstance(envelope, Mapping):
        raise TypeError("strategy snapshot validation failed: root must be an object")
    errors = sorted(
        _VALIDATOR.iter_errors(envelope),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(
            "strategy snapshot validation failed at "
            f"{_error_location(error)}: {error.message}"
        )


def load_strategy_snapshot(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"strategy snapshot validation failed: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TypeError("strategy snapshot validation failed: root must be an object")
    validate_strategy_snapshot(payload)
    return payload
