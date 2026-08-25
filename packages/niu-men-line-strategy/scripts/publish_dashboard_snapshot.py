"""Publish a validated Dashboard research snapshot from existing OOS artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_dashboard_snapshot import (
    build_snapshot,
    validate_dashboard_snapshot,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oos-json", type=Path, required=True)
    parser.add_argument("--research-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-generated-at")
    return parser


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} 不存在：{path}")


def publish_snapshot(
    *,
    oos_json: Path,
    research_manifest: Path,
    output: Path,
    snapshot_generated_at: str | None = None,
) -> dict[str, object]:
    _require_file(oos_json, "OOS manifest")
    _require_file(research_manifest, "数据平台 manifest")

    snapshot = build_snapshot(
        oos_json=oos_json,
        research_manifest=research_manifest,
        snapshot_generated_at=snapshot_generated_at,
    )
    validate_dashboard_snapshot(snapshot)
    if snapshot["quality"]["checks"]["oosRowsPresent"] is not True:  # type: ignore[index]
        raise ValueError("OOS 记录为空，拒绝发布 Dashboard 快照")

    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(serialized)

    os.replace(temporary, output)
    return snapshot


def main() -> None:
    args = _parser().parse_args()
    try:
        snapshot = publish_snapshot(
            oos_json=args.oos_json,
            research_manifest=args.research_manifest,
            output=args.output,
            snapshot_generated_at=args.snapshot_generated_at,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Dashboard 快照发布失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
