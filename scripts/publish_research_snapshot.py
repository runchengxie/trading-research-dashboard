"""Publish a validated research snapshot into the Dashboard static assets.

The producer (Niu Men OOS export or any strategy run) writes a snapshot JSON
file anywhere outside Git. This script is the only supported way to move it
into ``apps/dashboard/web/public/research.json``:

1. validate the candidate against the canonical contract and provenance rules
   BEFORE touching the Dashboard tree;
2. replace the published file atomically;
3. re-run the Dashboard static-asset validation; restore the previous file on
   any failure so the last valid snapshot is never lost;
4. optionally open a scoped update PR containing only the snapshot file.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_core.provenance import validate_provenance_consistency
from research_core.snapshot import validate_snapshot

DASHBOARD_ROOT = Path(__file__).resolve().parents[1] / "apps" / "dashboard"
RESEARCH_PATH = DASHBOARD_ROOT / "web" / "public" / "research.json"
DATA_PATH = DASHBOARD_ROOT / "web" / "public" / "data.json"

BRANCH_PREFIX = "publish/research-snapshot"


def _load_static_validator():
    """Load the Dashboard static-asset validator from its own tree."""

    module_path = DASHBOARD_ROOT / "scripts" / "validate_static_assets.py"
    spec = importlib.util.spec_from_file_location(
        "dashboard_validate_static_assets", module_path
    )
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load static validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_snapshots


validate_dashboard_snapshots = _load_static_validator()


def _load_candidate(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"snapshot input is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"snapshot input is not valid JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("snapshot input must be a JSON object")
    return payload


def _validate_candidate(payload: dict) -> None:
    validate_snapshot(payload)
    validate_provenance_consistency(payload)


def _write_atomic(target: Path, payload: dict) -> None:
    handle, temp_name = tempfile.mkstemp(
        dir=target.parent, prefix=".research.", suffix=".json"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def publish(snapshot_path: Path, *, data_path: Path = DATA_PATH, target: Path = RESEARCH_PATH) -> Path:
    """Validate and atomically publish ``snapshot_path``; return the target path."""

    payload = _load_candidate(snapshot_path)

    # Gate 1: contract + provenance validation happens before any write.
    _validate_candidate(payload)

    previous = target.read_bytes() if target.exists() else None
    _write_atomic(target, payload)
    try:
        validate_dashboard_snapshots(data_path=data_path, research_path=target)
    except BaseException:
        # Gate 2 failed: never leave the Dashboard without its last valid snapshot.
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(previous)
        raise
    return target


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(command)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def open_update_pr(repo_root: Path, target: Path, *, base: str | None = None) -> str:
    """Commit only the snapshot file on a dedicated branch and open an update PR."""

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch = f"{BRANCH_PREFIX}-{stamp}"
    default_branch = base or _run(["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"])
    _run(["git", "checkout", "-b", branch], cwd=repo_root)
    try:
        _run(["git", "add", "--", str(target.relative_to(repo_root))], cwd=repo_root)
        data_date = json.loads(target.read_text(encoding="utf-8")).get("source", {}).get("dataDate", "unknown")
        _run(
            [
                "git",
                "commit",
                "-m",
                f"chore: publish research snapshot for {data_date}",
            ],
            cwd=repo_root,
        )
        _run(["git", "push", "-u", "origin", branch], cwd=repo_root)
        title = f"chore: publish research snapshot for {data_date}"
        body = (
            "Automated research snapshot publication.\n\n"
            f"- source wire version: {json.loads(target.read_text(encoding='utf-8')).get('schemaVersion', 'unknown')}\n"
            f"- data date: {data_date}\n"
            "- validated against the canonical schema and provenance rules before this PR\n"
            "- review scope is limited to the published snapshot file"
        )
        url = _run(["gh", "pr", "create", "--base", default_branch, "--title", title, "--body", body], cwd=repo_root)
    except BaseException:
        _run(["git", "checkout", default_branch], cwd=repo_root)
        raise
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True, help="candidate snapshot JSON produced by a research run")
    parser.add_argument("--open-pr", action="store_true", help="push a scoped branch and open an update PR after publishing")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    target = publish(args.snapshot.resolve())

    print(f"published validated snapshot: {target}")
    if args.open_pr:
        url = open_update_pr(repo_root, RESEARCH_PATH)
        print(f"update PR: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
