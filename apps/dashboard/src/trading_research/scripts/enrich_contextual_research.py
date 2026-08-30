from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from trading_research.dashboard.contextual_research import build_contextual_snapshot


def enrich_document(
    document: Mapping[str, Any],
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    generated_at = document.get("generatedAt")
    stocks = document.get("stocks")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("dashboard document requires generatedAt")
    if not isinstance(stocks, list):
        raise ValueError("dashboard document requires stocks array")

    result = dict(document)
    result["contextualResearch"] = build_contextual_snapshot(
        [stock for stock in stocks if isinstance(stock, Mapping)],
        generated_at=generated_at,
        events=events,
    )
    return result


def _load_events(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("event input must be a JSON array")
    return [item for item in payload if isinstance(item, Mapping)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为 Dashboard data.json 增加 contextualResearch 研究层"
    )
    parser.add_argument("--input", required=True, help="现有 Dashboard data.json")
    parser.add_argument("--output", default=None, help="输出路径；默认原子覆盖 input")
    parser.add_argument("--events", default=None, help="可选标准化经济/公司事件 JSON 数组")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("dashboard document root must be an object")

    enriched = enrich_document(
        document,
        events=_load_events(Path(args.events)) if args.events else None,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(output_path)


if __name__ == "__main__":
    main()
