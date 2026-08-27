#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_VALID_MODES = {"shadow", "authoritative"}


def build_runtime_manifest(
    *,
    data: dict[str, Any],
    mode: str,
    commit: str,
    run_id: str | None,
    public_url: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(_VALID_MODES)}")

    generated_at = data.get("generatedAt")
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("data.generatedAt must be a non-empty string")

    normalized_commit = commit.strip()
    if not normalized_commit:
        raise ValueError("commit must be non-empty")

    normalized_public_url = public_url.strip() if isinstance(public_url, str) else None
    if normalized_mode == "authoritative" and not normalized_public_url:
        raise ValueError("authoritative runtime manifest requires a public URL")
    if normalized_mode == "shadow":
        normalized_public_url = None

    created_at = now or datetime.now(UTC)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    return {
        "schemaVersion": "trading_research.runtime_manifest.v1",
        "mode": normalized_mode,
        "commit": normalized_commit,
        "workflowRunId": str(run_id).strip() if run_id is not None else None,
        "dataGeneratedAt": generated_at.strip(),
        "createdAt": created_at.isoformat(),
        "publicUrl": normalized_public_url,
    }


def _load_data(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read Dashboard data from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a Dashboard runtime manifest")
    parser.add_argument("--data-json", type=Path, required=True)
    parser.add_argument("--mode", required=True, choices=sorted(_VALID_MODES))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--public-url")
    args = parser.parse_args()

    manifest = build_runtime_manifest(
        data=_load_data(args.data_json),
        mode=args.mode,
        commit=args.commit,
        run_id=args.run_id,
        public_url=args.public_url,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote runtime manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
