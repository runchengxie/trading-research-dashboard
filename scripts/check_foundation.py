"""Validate the M1 monorepo boundary and foundation files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REQUIRED_DIRECTORIES = (
    "apps/dashboard",
    "packages/research-core",
    "packages/niu-men-line-strategy",
    "docs/migration",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
    "scripts",
    "tests",
)

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "pyproject.toml",
    "uv.lock",
    "docs/migration/README.md",
    "docs/migration/dashboard-import.md",
    "docs/migration/source-commits.md",
    "apps/dashboard/README.md",
    "packages/research-core/README.md",
    "packages/niu-men-line-strategy/README.md",
    "docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md",
    "docs/superpowers/plans/2026-08-26-monorepo-foundation.md",
    ".github/workflows/foundation.yml",
)

M1_FOUNDATION_TRACKED_FILES = frozenset(
    (
        ".github/workflows/deploy-dashboard.yml",
        ".github/workflows/foundation.yml",
        ".gitignore",
        "AGENTS.md",
        "README.md",
        "docs/migration/dashboard-import.md",
        "docs/migration/README.md",
        "docs/migration/source-commits.md",
        "docs/superpowers/plans/2026-08-26-m1-dashboard-import.md",
        "docs/superpowers/plans/2026-08-26-monorepo-foundation.md",
        "docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md",
        "docs/superpowers/specs/2026-08-26-m1-history-preserving-imports-design.md",
        "packages/niu-men-line-strategy/README.md",
        "packages/research-core/README.md",
        "pyproject.toml",
        "scripts/check_foundation.py",
        "tests/test_foundation.py",
        "uv.lock",
    )
)

DASHBOARD_ALLOWED_DIRECTORY_PREFIXES = (
    "apps/dashboard/backtest/",
    "apps/dashboard/scripts/",
    "apps/dashboard/src/",
    "apps/dashboard/tests/",
    "apps/dashboard/web/src/",
    "apps/dashboard/web/tests/",
)

DASHBOARD_ALLOWED_FILES = frozenset(
    (
        "apps/dashboard/.gitignore",
        "apps/dashboard/README.md",
        "apps/dashboard/docs/backtest.md",
        "apps/dashboard/docs/cloudflare-workers.md",
        "apps/dashboard/docs/configuration.md",
        "apps/dashboard/docs/data-sources.md",
        "apps/dashboard/docs/indicators.md",
        "apps/dashboard/docs/outputs.md",
        "apps/dashboard/docs/research-snapshot.md",
        "apps/dashboard/docs/troubleshooting.md",
        "apps/dashboard/docs/web-frontend.md",
        "apps/dashboard/pyproject.toml",
        "apps/dashboard/schemas/research-snapshot.schema.json",
        "apps/dashboard/uv.lock",
        "apps/dashboard/wrangler.jsonc",
        "apps/dashboard/web/.gitignore",
        "apps/dashboard/web/index.html",
        "apps/dashboard/web/package-lock.json",
        "apps/dashboard/web/package.json",
        "apps/dashboard/web/playwright.config.mjs",
        "apps/dashboard/web/public/data.json",
        "apps/dashboard/web/public/research.json",
        "apps/dashboard/web/tsconfig.json",
        "apps/dashboard/web/vite.config.ts",
    )
)

FORBIDDEN_TRACKED_DIRECTORY_PREFIXES = ()

FORBIDDEN_TRACKED_PATH_PATTERNS = (
    re.compile(r"(?:^|/)data/raw(?:/|$)"),
    re.compile(r"(?:^|/)artifacts(?:/|$)"),
)

FORBIDDEN_CREDENTIAL_NAME_PATTERN = re.compile(
    r"(?:^\.env.*$|.*(?:credential|secret|token|password).*|.*\.(?:pem|key|p12|pfx)$)",
    re.IGNORECASE,
)

FORBIDDEN_DIRECTORIES = (
    "research-workspace",
    "market-data-platform",
    "etf-minute-fetcher",
)

PLACEHOLDER_PATTERN = re.compile(r"\b(?:TBD|TODO|FIXME)\b")


def is_forbidden_tracked_file(relative: str) -> bool:
    """Return whether a tracked path crosses a protected M1 boundary."""
    if relative.startswith(FORBIDDEN_TRACKED_DIRECTORY_PREFIXES):
        return True
    if any(pattern.search(relative) for pattern in FORBIDDEN_TRACKED_PATH_PATTERNS):
        return True
    return bool(FORBIDDEN_CREDENTIAL_NAME_PATTERN.fullmatch(relative.rsplit("/", 1)[-1]))


def is_allowed_tracked_file(relative: str) -> bool:
    """Return whether a tracked path is an M1 foundation or manifest path."""
    if is_forbidden_tracked_file(relative):
        return False
    return relative in M1_FOUNDATION_TRACKED_FILES or relative in DASHBOARD_ALLOWED_FILES or relative.startswith(
        DASHBOARD_ALLOWED_DIRECTORY_PREFIXES
    )


def is_ignored_path(root: Path, relative: Path) -> bool:
    """Return whether a path is excluded by the repository ignore rules."""
    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", str(relative)],
        capture_output=True,
        check=False,
        text=True,
    )
    return ignored.returncode == 0


def validate_foundation(root: Path) -> list[str]:
    """Return deterministic validation errors for the M1 repository shape."""
    errors: list[str] = []
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"required directory missing: {relative}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"required file missing: {relative}")
    for relative in FORBIDDEN_DIRECTORIES:
        if (root / relative).exists():
            errors.append(f"forbidden external project directory present: {relative}")

    tracked_files = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        check=False,
        text=True,
    )
    if tracked_files.returncode:
        errors.append("unable to inspect tracked files for the M1 boundary")
    else:
        for relative in tracked_files.stdout.splitlines():
            if not is_allowed_tracked_file(relative):
                errors.append(f"tracked file is not allowed during M1: {relative}")

    tracked_modes = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage"],
        capture_output=True,
        check=False,
        text=True,
    )
    if tracked_modes.returncode:
        errors.append("unable to inspect tracked file modes for the M1 boundary")
    else:
        for entry in tracked_modes.stdout.splitlines():
            metadata, separator, relative = entry.partition("\t")
            if separator and metadata.startswith("160000 "):
                errors.append(f"gitlink is not allowed during M1: {relative}")

    for markdown in sorted(root.rglob("*.md")):
        if ".git" in markdown.parts or any(
            part.lstrip(".") == "superpowers" for part in markdown.parts
        ):
            continue
        if is_ignored_path(root, markdown.relative_to(root)):
            continue
        text = markdown.read_text(encoding="utf-8")
        if PLACEHOLDER_PATTERN.search(text):
            errors.append(
                "placeholder marker found in documentation: "
                f"{markdown.relative_to(root)}"
            )
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_foundation(root)
    if errors:
        print("Foundation check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Foundation check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
