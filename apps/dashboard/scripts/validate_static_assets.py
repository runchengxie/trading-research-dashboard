"""Validate the static JSON snapshots required by the Dashboard build."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_core import validate_conditional_research, validate_contextual_snapshot

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "web" / "public" / "data.json"
RESEARCH_PATH = ROOT / "web" / "public" / "research.json"


def _load_json(path: Path) -> object:
    if not path.is_file():
        raise ValueError(f"required Dashboard snapshot is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Dashboard snapshot is not valid JSON: {path}: {exc}") from exc


def validate_snapshots(
    data_path: Path = DATA_PATH,
    research_path: Path = RESEARCH_PATH,
    *,
    require_contextual: bool = False,
) -> None:
    data = _load_json(data_path)
    if not isinstance(data, dict):
        raise ValueError("data.json must contain a JSON object")
    if not isinstance(data.get("generatedAt"), str) or not data["generatedAt"]:
        raise ValueError("data.json.generatedAt must be a non-empty string")
    stocks = data.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise ValueError("data.json.stocks must contain at least one instrument")

    if require_contextual:
        contextual = data.get("contextualResearch")
        if not isinstance(contextual, dict):
            raise ValueError(
                "data.json.contextualResearch is required for authoritative release"
            )
        coverage = contextual.get("coverage")
        if not isinstance(coverage, dict) or coverage.get("evaluated", 0) <= 0:
            raise ValueError(
                "data.json.contextualResearch.coverage.evaluated must be positive"
            )

    contextual = data.get("contextualResearch")
    if contextual is not None:
        if not isinstance(contextual, dict):
            raise ValueError("data.json.contextualResearch must be an object")
        validate_contextual_snapshot(contextual)

    conditional = data.get("conditionalResearch")
    if conditional is not None:
        if not isinstance(conditional, dict):
            raise ValueError("data.json.conditionalResearch must be an object")
        validate_conditional_research(conditional)

    if research_path.is_file():
        research = _load_json(research_path)
        if not isinstance(research, dict):
            raise ValueError("research.json must contain a JSON object")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-contextual", action="store_true")
    args = parser.parse_args()
    validate_snapshots(require_contextual=args.require_contextual)
    print(f"Dashboard snapshots valid: {DATA_PATH} ({len(json.loads(DATA_PATH.read_text(encoding='utf-8'))['stocks'])} instruments)")
