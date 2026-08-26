"""Validate the static JSON snapshots required by the Dashboard build."""

from __future__ import annotations

import json
from pathlib import Path


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
) -> None:
    data = _load_json(data_path)
    if not isinstance(data, dict):
        raise ValueError("data.json must contain a JSON object")
    if not isinstance(data.get("generatedAt"), str) or not data["generatedAt"]:
        raise ValueError("data.json.generatedAt must be a non-empty string")
    stocks = data.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise ValueError("data.json.stocks must contain at least one instrument")

    if research_path.is_file():
        research = _load_json(research_path)
        if not isinstance(research, dict):
            raise ValueError("research.json must contain a JSON object")


if __name__ == "__main__":
    validate_snapshots()
    print(f"Dashboard snapshots valid: {DATA_PATH} ({len(json.loads(DATA_PATH.read_text(encoding='utf-8'))['stocks'])} instruments)")
