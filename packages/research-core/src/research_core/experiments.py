from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator

RESEARCH_EXPERIMENT_VERSION = "trading_research.research_experiment.v1"


def _load_schema(name: str) -> dict[str, Any]:
    resource = files("research_core.schemas").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


_RESEARCH_EXPERIMENT_VALIDATOR = Draft202012Validator(
    _load_schema("research-experiment.v1.schema.json")
)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def _validate_schema(kind: str, validator: Validator, payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{kind} validation failed: root must be an object")
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(f"{kind} validation failed at {_error_location(error)}: {error.message}")


def _ensure_unique(items: Sequence[Mapping[str, Any]], field: str, kind: str) -> None:
    values = [item[field] for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{kind} validation failed: duplicate {field}")


def validate_research_experiment(payload: Mapping[str, Any]) -> None:
    _validate_schema("research experiment", _RESEARCH_EXPERIMENT_VALIDATOR, payload)
    variants = payload["variants"]
    scorecard = payload["scorecard"]
    _ensure_unique(variants, "variantId", "research experiment")
    _ensure_unique(scorecard, "metricId", "research experiment")
    variant_ids = {variant["variantId"] for variant in variants}
    if payload["baselineVariantId"] not in variant_ids:
        raise ValueError(
            "research experiment validation failed: baselineVariantId must reference a variant"
        )
