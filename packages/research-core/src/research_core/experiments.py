from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator

RESEARCH_EXPERIMENT_VERSION = "trading_research.research_experiment.v1"
AGENT_RUN_VERSION = "trading_research.agent_run.v1"
RESEARCH_EVIDENCE_VERSION = "trading_research.research_evidence.v1"
EVAL_RESULT_VERSION = "trading_research.eval_result.v1"

_TERMINAL_RUN_STATUSES = frozenset(
    {"completed", "incomplete", "failed", "timeout", "budget_limited", "cancelled"}
)


def _load_schema(name: str) -> dict[str, Any]:
    resource = files("research_core.schemas").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


_RESEARCH_EXPERIMENT_VALIDATOR = Draft202012Validator(
    _load_schema("research-experiment.v1.schema.json")
)
_AGENT_RUN_VALIDATOR = Draft202012Validator(_load_schema("agent-run.v1.schema.json"))
_RESEARCH_EVIDENCE_VALIDATOR = Draft202012Validator(
    _load_schema("research-evidence.v1.schema.json")
)
_EVAL_RESULT_VALIDATOR = Draft202012Validator(_load_schema("eval-result.v1.schema.json"))


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


def _validate_task_graph(tasks: Sequence[Mapping[str, Any]]) -> None:
    task_ids = {task["taskId"] for task in tasks}
    dependencies = {task["taskId"]: task["dependsOn"] for task in tasks}
    for task_id, depends_on in dependencies.items():
        for dependency in depends_on:
            if dependency not in task_ids:
                raise ValueError(
                    f"agent run validation failed: unknown dependency {dependency} for task {task_id}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError("agent run validation failed: task dependency cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id)


def validate_agent_run(payload: Mapping[str, Any]) -> None:
    _validate_schema("agent run", _AGENT_RUN_VALIDATOR, payload)
    tasks = payload["tasks"]
    _ensure_unique(tasks, "taskId", "agent run")
    _validate_task_graph(tasks)
    if payload["status"] in _TERMINAL_RUN_STATUSES and "completedAt" not in payload:
        raise ValueError("agent run validation failed: completedAt is required for terminal status")
    for task in tasks:
        if task["status"] in _TERMINAL_RUN_STATUSES and "completedAt" not in task:
            raise ValueError(
                f"agent run validation failed: completedAt is required for terminal task {task['taskId']}"
            )
    if payload["status"] == "completed" and any(
        task["status"] != "completed" for task in tasks
    ):
        raise ValueError("agent run validation failed: completed run requires completed tasks")


def validate_research_evidence(payload: Mapping[str, Any]) -> None:
    _validate_schema("research evidence", _RESEARCH_EVIDENCE_VALIDATOR, payload)
    point_in_time = payload["pointInTime"]
    assurance = point_in_time["assurance"]
    strict = point_in_time["strict"]
    eligible_as_oos = point_in_time["eligibleAsOosEvidence"]
    if strict and assurance != "strict_replay":
        raise ValueError(
            "research evidence validation failed: strict point-in-time requires strict_replay assurance"
        )
    if eligible_as_oos and assurance not in {"externally_timestamped", "strict_replay"}:
        raise ValueError(
            "research evidence validation failed: OOS evidence eligibility requires external timing proof"
        )


def validate_eval_result(payload: Mapping[str, Any]) -> None:
    _validate_schema("evaluation result", _EVAL_RESULT_VALIDATOR, payload)
    _ensure_unique(payload["metrics"], "metricId", "evaluation result")
