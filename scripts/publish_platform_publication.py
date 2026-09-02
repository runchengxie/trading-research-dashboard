"""Publish a validated research-platform bundle into Dashboard static assets.

This is the local/production-runner path for environments where the research
workspace intentionally does not use GitHub Actions. It installs only the public
Dashboard projection and can open a scoped static-data PR.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_SRC = REPO_ROOT / "apps" / "dashboard" / "src"
DASHBOARD_PUBLIC = REPO_ROOT / "apps" / "dashboard" / "web" / "public"
sys.path.insert(0, str(DASHBOARD_SRC))

from trading_research.platform_publication import install_platform_publication


PUBLICATION_PATHS = (
    Path("apps/dashboard/web/public/platform-publication.json"),
    Path("apps/dashboard/web/public/platform"),
)


def _run(command: list[str], *, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(command)}\n{result.stderr.strip()}\n{result.stdout.strip()}"
        )
    return result.stdout.strip()


def publish(bundle_root: Path) -> dict[str, object]:
    return install_platform_publication(bundle_root, DASHBOARD_PUBLIC)


def open_update_pr(*, base: str | None = None) -> str:
    dirty_before = _run(["git", "status", "--porcelain"])
    allowed = {str(path) for path in PUBLICATION_PATHS}
    unrelated = []
    for line in dirty_before.splitlines():
        path = line[3:].strip() if len(line) > 3 else ""
        if path and not any(path == item or path.startswith(f"{item}/") for item in allowed):
            unrelated.append(path)
    if unrelated:
        raise SystemExit(
            "refusing to open publication PR with unrelated working-tree changes: "
            + ", ".join(sorted(set(unrelated)))
        )

    default_branch = base or _run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"]
    )
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    branch = f"publish/platform-publication-{stamp}"
    _run(["git", "switch", "-c", branch])
    try:
        _run(["git", "add", "--", *(str(path) for path in PUBLICATION_PATHS)])
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=REPO_ROOT,
            check=False,
        )
        if staged.returncode == 0:
            return "unchanged"
        title = "chore: publish research platform evidence"
        _run(["git", "commit", "-m", title])
        _run(["git", "push", "-u", "origin", branch])
        body = (
            "Scoped research-platform publication.\n\n"
            "The local publisher validated the publication manifest, verified SHA-256 identities, "
            "filtered out non-public/non-Dashboard projections, and staged only "
            "`platform-publication.json` plus `platform/`."
        )
        return _run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                default_branch,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                body,
            ]
        )
    finally:
        _run(["git", "switch", default_branch])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--open-pr", action="store_true")
    parser.add_argument("--base")
    args = parser.parse_args(argv)

    result = publish(args.bundle_root)
    output: dict[str, object] = {"publication": result}
    if args.open_pr:
        output["pull_request"] = open_update_pr(base=args.base)
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
