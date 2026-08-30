from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from research_core import validate_contextual_snapshot

from trading_research.dashboard.contextual_history import aggregate_contextual_history
from trading_research.dashboard.contextual_research import build_contextual_snapshot


def enrich_document(
    document: Mapping[str, Any],
    *,
    events: Sequence[Mapping[str, Any]] | None = None,
    history_documents: Sequence[Mapping[str, Any]] | None = None,
    strategy_outcomes: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    generated_at = document.get("generatedAt")
    stocks = document.get("stocks")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("dashboard document requires generatedAt")
    if not isinstance(stocks, list):
        raise ValueError("dashboard document requires stocks array")

    result = dict(document)
    contextual = build_contextual_snapshot(
        [stock for stock in stocks if isinstance(stock, Mapping)],
        generated_at=generated_at,
        events=events,
    )
    result["contextualResearch"] = contextual
    if history_documents:
        snapshots = [contextual]
        seen = {_snapshot_identity(contextual)}
        for index, history_document in enumerate(history_documents):
            history_context = _extract_contextual(history_document, index=index)
            identity = _snapshot_identity(history_context)
            if identity in seen:
                continue
            seen.add(identity)
            snapshots.append(history_context)
        result["conditionalResearch"] = aggregate_contextual_history(
            snapshots,
            strategy_outcomes=strategy_outcomes,
            generated_at=generated_at,
        )
    return result


def _snapshot_identity(snapshot: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    date = str(snapshot.get("dataDate") or "")
    contexts = snapshot.get("contexts")
    codes = []
    if isinstance(contexts, Sequence) and not isinstance(contexts, (str, bytes)):
        for context in contexts:
            if not isinstance(context, Mapping):
                continue
            instrument = context.get("instrument")
            if isinstance(instrument, Mapping) and instrument.get("code"):
                codes.append(str(instrument["code"]))
    return date, tuple(sorted(codes))


def _extract_contextual(document: Mapping[str, Any], *, index: int) -> Mapping[str, Any]:
    contextual = document.get("contextualResearch")
    if contextual is None and document.get("schemaVersion") == "trading_research.contextual_snapshot.v1":
        contextual = document
    if not isinstance(contextual, Mapping):
        raise ValueError(f"history[{index}] requires contextualResearch snapshot")
    validate_contextual_snapshot(contextual)
    return contextual


def _load_events(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("event input must be a JSON array")
    return [item for item in payload if isinstance(item, Mapping)]


def _load_history(paths: Sequence[Path]) -> list[Mapping[str, Any]]:
    documents: list[Mapping[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            documents.extend(item for item in payload if isinstance(item, Mapping))
        elif isinstance(payload, Mapping):
            documents.append(payload)
        else:
            raise ValueError("history input must contain a JSON object or array")
    return documents


def _load_strategy_outcomes(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("strategy outcome input must be a JSON array")
    return [item for item in payload if isinstance(item, Mapping)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为 Dashboard data.json 增加 contextualResearch 研究层"
    )
    parser.add_argument("--input", required=True, help="现有 Dashboard data.json")
    parser.add_argument("--output", default=None, help="输出路径；默认原子覆盖 input")
    parser.add_argument("--events", default=None, help="可选标准化经济/公司事件 JSON 数组")
    parser.add_argument(
        "--history",
        action="append",
        default=[],
        help="可重复传入历史 Dashboard/contextual snapshot JSON",
    )
    parser.add_argument(
        "--strategy-outcomes",
        default=None,
        help="可选标准化策略 outcome JSON 数组",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("dashboard document root must be an object")

    enriched = enrich_document(
        document,
        events=_load_events(Path(args.events)) if args.events else None,
        history_documents=_load_history([Path(path) for path in args.history]) if args.history else None,
        strategy_outcomes=(
            _load_strategy_outcomes(Path(args.strategy_outcomes))
            if args.strategy_outcomes
            else None
        ),
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
