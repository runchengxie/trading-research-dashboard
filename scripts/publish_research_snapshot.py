"""Publish a validated strategy research snapshot into Dashboard static assets.

The producer writes a snapshot JSON file outside Git. This script is the
supported boundary for moving reviewed research results into the Dashboard:

1. select the publication target explicitly by strategy id;
2. validate the candidate contract, identity, and provenance before writes;
3. replace only the selected static snapshot atomically;
4. re-run Dashboard static-asset validation and restore the prior snapshot on
   any failure;
5. optionally open a scoped update PR containing only that snapshot file.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_core.provenance import validate_provenance_consistency
from research_core.snapshot import validate_snapshot
from research_core.strategy_snapshot import validate_strategy_snapshot

DASHBOARD_ROOT = Path(__file__).resolve().parents[1] / "apps" / "dashboard"
DASHBOARD_PUBLIC = DASHBOARD_ROOT / "web" / "public"
RESEARCH_PATH = DASHBOARD_PUBLIC / "research.json"
R_BREAKER_RESEARCH_PATH = DASHBOARD_PUBLIC / "rbreaker-research.json"
DATA_PATH = DASHBOARD_PUBLIC / "data.json"

DEFAULT_STRATEGY_ID = "niu-men-line"
_RBREAKER_REQUIRED_PROVENANCE = (
    "researchCommit",
    "dataPlatform",
    "dataPlatformSchemaVersion",
    "dataPlatformGeneratedAt",
    "oosSchemaVersion",
    "oosGeneratedAt",
    "artifactRunId",
    "inputSha256",
)


@dataclass(frozen=True, slots=True)
class PublicationTarget:
    strategy_id: str
    path: Path
    branch_prefix: str
    validator: Callable[[dict], None]


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
        raise SystemExit(
            f"snapshot input is not valid JSON: {path}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit("snapshot input must be a JSON object")
    return payload


def _validate_niu_men_candidate(payload: dict) -> None:
    validate_snapshot(payload)
    validate_provenance_consistency(payload)


def _validate_rbreaker_candidate(payload: dict) -> None:
    validate_strategy_snapshot(payload)
    strategy = payload["strategy"]
    if strategy["id"] != "r-breaker":
        raise ValueError("R-Breaker publication strategy.id must be r-breaker")
    if payload["quality"]["status"] != "pass":
        raise ValueError("R-Breaker publication requires quality.status=pass")

    provenance = payload["provenance"]
    missing = [
        field
        for field in _RBREAKER_REQUIRED_PROVENANCE
        if not isinstance(provenance.get(field), str) or not provenance[field].strip()
    ]
    if missing:
        raise ValueError(
            "R-Breaker publication provenance is incomplete: "
            + ", ".join(missing)
        )


PUBLICATION_TARGETS = {
    "niu-men-line": PublicationTarget(
        strategy_id="niu-men-line",
        path=RESEARCH_PATH,
        branch_prefix="publish/niu-men-line-snapshot",
        validator=_validate_niu_men_candidate,
    ),
    "r-breaker": PublicationTarget(
        strategy_id="r-breaker",
        path=R_BREAKER_RESEARCH_PATH,
        branch_prefix="publish/r-breaker-snapshot",
        validator=_validate_rbreaker_candidate,
    ),
}


def publication_target(strategy_id: str) -> PublicationTarget:
    try:
        return PUBLICATION_TARGETS[strategy_id]
    except KeyError as exc:
        choices = ", ".join(sorted(PUBLICATION_TARGETS))
        raise ValueError(
            f"unsupported strategy_id={strategy_id!r}; choices: {choices}"
        ) from exc


def _write_atomic(target: Path, payload: dict) -> None:
    handle, temp_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.stem}.", suffix=".json"
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


def publish(
    snapshot_path: Path,
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    data_path: Path = DATA_PATH,
    target: Path | None = None,
) -> Path:
    """Validate and atomically publish ``snapshot_path`` for ``strategy_id``."""

    publication = publication_target(strategy_id)
    destination = target or publication.path
    payload = _load_candidate(snapshot_path)

    # Gate 1: contract + strategy identity + provenance before any target write.
    publication.validator(payload)

    previous = destination.read_bytes() if destination.exists() else None
    _write_atomic(destination, payload)
    try:
        # The static validator currently owns data.json + Niu Men compatibility.
        # R-Breaker has already passed its canonical generic schema above.
        research_path = (
            destination
            if strategy_id == DEFAULT_STRATEGY_ID
            else data_path.parent / RESEARCH_PATH.name
        )
        validate_dashboard_snapshots(
            data_path=data_path,
            research_path=research_path,
        )
    except BaseException:
        # Gate 2 failed: never lose the last known-good strategy snapshot.
        if previous is None:
            destination.unlink(missing_ok=True)
        else:
            destination.write_bytes(previous)
        raise
    return destination


def _snapshot_data_date(payload: dict) -> str:
    generic_date = payload.get("dataDate")
    if isinstance(generic_date, str) and generic_date.strip():
        return generic_date
    source = payload.get("source")
    if isinstance(source, dict):
        legacy_date = source.get("dataDate")
        if isinstance(legacy_date, str) and legacy_date.strip():
            return legacy_date
    return "unknown"


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(command)}\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def open_update_pr(
    repo_root: Path,
    target: Path,
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    base: str | None = None,
) -> str:
    """Commit one strategy snapshot on a dedicated branch and open its PR."""

    publication = publication_target(strategy_id)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch = f"{publication.branch_prefix}-{stamp}"
    default_branch = base or _run(
        [
            "gh",
            "repo",
            "view",
            "--json",
            "defaultBranchRef",
            "--jq",
            ".defaultBranchRef.name",
        ]
    )
    _run(["git", "checkout", "-b", branch], cwd=repo_root)
    try:
        _run(
            ["git", "add", "--", str(target.relative_to(repo_root))],
            cwd=repo_root,
        )
        payload = json.loads(target.read_text(encoding="utf-8"))
        data_date = _snapshot_data_date(payload)
        title = f"chore: publish {strategy_id} snapshot for {data_date}"
        _run(["git", "commit", "-m", title], cwd=repo_root)
        _run(["git", "push", "-u", "origin", branch], cwd=repo_root)
        body = (
            "Automated strategy research snapshot publication.\n\n"
            f"- strategy id: {strategy_id}\n"
            f"- source wire version: {payload.get('schemaVersion', 'unknown')}\n"
            f"- data date: {data_date}\n"
            "- validated against the strategy contract and provenance rules before this PR\n"
            "- review scope is limited to the published snapshot file"
        )
        url = _run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                default_branch,
                "--title",
                title,
                "--body",
                body,
            ],
            cwd=repo_root,
        )
    except BaseException:
        _run(["git", "checkout", default_branch], cwd=repo_root)
        raise
    return url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="candidate snapshot JSON produced by a research run",
    )
    parser.add_argument(
        "--strategy-id",
        choices=tuple(PUBLICATION_TARGETS),
        default=DEFAULT_STRATEGY_ID,
        help="explicit Dashboard strategy publication target",
    )
    parser.add_argument(
        "--open-pr",
        action="store_true",
        help="push a scoped branch and open an update PR after publishing",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    target = publish(
        args.snapshot.resolve(),
        strategy_id=args.strategy_id,
    )

    print(f"published validated snapshot: {target}")
    if args.open_pr:
        url = open_update_pr(
            repo_root,
            target,
            strategy_id=args.strategy_id,
        )
        print(f"update PR: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
