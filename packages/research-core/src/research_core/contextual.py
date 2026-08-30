from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

MARKET_CONTEXT_VERSION = "trading_research.market_context.v1"
SETUP_EVENT_VERSION = "trading_research.setup_event.v1"
EVENT_STUDY_VERSION = "trading_research.event_study.v1"
CONTEXTUAL_SNAPSHOT_VERSION = "trading_research.contextual_snapshot.v1"


def _load_schema(name: str) -> dict[str, Any]:
    resource = files("research_core.schemas").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


_MARKET_CONTEXT_VALIDATOR = Draft202012Validator(
    _load_schema("market-context.v1.schema.json")
)
_SETUP_EVENT_VALIDATOR = Draft202012Validator(_load_schema("setup-event.v1.schema.json"))
_EVENT_STUDY_VALIDATOR = Draft202012Validator(_load_schema("event-study.v1.schema.json"))
_CONTEXTUAL_SNAPSHOT_VALIDATOR = Draft202012Validator(
    _load_schema("contextual-snapshot.v1.schema.json")
)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def _validate(
    kind: str,
    validator: Draft202012Validator,
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{kind} validation failed: root must be an object")
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(
            f"{kind} validation failed at {_error_location(error)}: {error.message}"
        )


def validate_market_context(payload: Mapping[str, Any]) -> None:
    _validate("market context", _MARKET_CONTEXT_VALIDATOR, payload)


def validate_setup_event(payload: Mapping[str, Any]) -> None:
    _validate("setup event", _SETUP_EVENT_VALIDATOR, payload)


def validate_event_study(payload: Mapping[str, Any]) -> None:
    _validate("event study", _EVENT_STUDY_VALIDATOR, payload)


def validate_contextual_snapshot(payload: Mapping[str, Any]) -> None:
    _validate("contextual snapshot", _CONTEXTUAL_SNAPSHOT_VALIDATOR, payload)
    for context in payload["contexts"]:
        validate_market_context(context)
    for event in payload["setupEvents"]:
        validate_setup_event(event)
    for study in payload["eventStudies"]:
        validate_event_study(study)


def load_contextual_snapshot(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"contextual snapshot validation failed: invalid JSON: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise TypeError("contextual snapshot validation failed: root must be an object")
    validate_contextual_snapshot(payload)
    return payload
