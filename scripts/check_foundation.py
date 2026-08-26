"""Validate the M0 monorepo boundary and foundation files."""

from __future__ import annotations

import re
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
    "docs/migration/source-commits.md",
    "apps/dashboard/README.md",
    "packages/research-core/README.md",
    "packages/niu-men-line-strategy/README.md",
    "docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md",
    "docs/superpowers/plans/2026-08-26-monorepo-foundation.md",
    ".github/workflows/foundation.yml",
)

FORBIDDEN_DIRECTORIES = (
    "research-workspace",
    "market-data-platform",
    "etf-minute-fetcher",
)

PLACEHOLDER_PATTERN = re.compile(r"\b(?:TBD|TODO|FIXME)\b")


def validate_foundation(root: Path) -> list[str]:
    """Return deterministic validation errors for the M0 repository shape."""
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

    for markdown in sorted(root.rglob("*.md")):
        if ".git" in markdown.parts or "superpowers" in markdown.parts:
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
