"""Validate the M1 monorepo boundary and foundation files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REQUIRED_DIRECTORIES = (
    "apps/dashboard",
    "apps/market-data-service",
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
    "docs/migration/niu-men-import.md",
    "docs/migration/source-commits.md",
    "apps/dashboard/README.md",
    "packages/research-core/README.md",
    "packages/niu-men-line-strategy/README.md",
    "docs/superpowers/specs/2026-08-26-trading-research-dashboard-monorepo-design.md",
    "docs/superpowers/plans/2026-08-26-monorepo-foundation.md",
    ".github/workflows/foundation.yml",
)

M1_FOUNDATION_TRACKED_FILES = frozenset(
    (
        ".github/workflows/dashboard-report.yml",
        ".github/workflows/deploy-dashboard.yml",
        ".github/workflows/foundation.yml",
        ".github/workflows/market-data-integration.yml",
        ".github/workflows/publish-rbreaker-snapshot.yml",
        ".github/workflows/publish-research-snapshot.yml",
        ".gitignore",
        ".env.example",
        "AGENTS.md",
        "README.md",
        "docs/migration/dashboard-import.md",
        "docs/migration/niu-men-import.md",
        "docs/migration/README.md",
        "docs/migration/source-commits.md",
        "apps/dashboard/docs/contextual-research.md",
        "packages/niu-men-line-strategy/README.md",
        "packages/research-core/README.md",
        "pyproject.toml",
        "scripts/check_foundation.py",
        "scripts/package_share.py",
        "scripts/publish_research_snapshot.py",
        "tests/test_foundation.py",
        "tests/test_publish_research_snapshot.py",
        "tests/test_share_package.py",
        "tests/test_rbreaker_publish_workflow.py",
        "tests/test_research_contract_sync.py",
        "tests/test_deploy_workflow.py",
        "tests/test_runtime_workflow.py",
        "uv.lock",
    )
)

SUPERPOWERS_ALLOWED_DIRECTORY_PREFIXES = (
    "docs/superpowers/plans/",
    "docs/superpowers/specs/",
)

DOCUMENTATION_ALLOWED_DIRECTORY_PREFIXES = (
    "docs/architecture/",
    "docs/capabilities/",
    "docs/migration/",
    "docs/operations/",
    "docs/roadmap/",
    "docs/maintenance/",
)

DOCUMENTATION_ALLOWED_FILES = frozenset(
    (
        "docs/README.md",
        "docs/getting-started.md",
    )
)

DASHBOARD_ALLOWED_DIRECTORY_PREFIXES = (
    "apps/dashboard/backtest/",
    "apps/dashboard/scripts/",
    "apps/dashboard/src/",
    "apps/dashboard/tests/",
    "apps/dashboard/web/scripts/",
    "apps/dashboard/web/src/",
    "apps/dashboard/web/tests/",
)

MARKET_DATA_ALLOWED_DIRECTORY_PREFIXES = (
    "apps/market-data-service/src/",
    "apps/market-data-service/tests/",
    "apps/market-data-service/docs/",
)

MARKET_DATA_ALLOWED_FILES = frozenset(
    (
        "apps/market-data-service/pyproject.toml",
        "apps/market-data-service/README.md",
    )
)

NIU_MEN_ALLOWED_DIRECTORY_PREFIXES = (
    "packages/niu-men-line-strategy/src/",
    "packages/niu-men-line-strategy/scripts/",
    "packages/niu-men-line-strategy/tests/",
)

RESEARCH_CORE_ALLOWED_DIRECTORY_PREFIXES = (
    "packages/research-core/src/",
    "packages/research-core/tests/",
)

RESEARCH_CORE_ALLOWED_FILES = frozenset(
    (
        "packages/research-core/pyproject.toml",
        "packages/research-core/README.md",
        "schemas/research-snapshot.schema.json",
    )
)

NIU_MEN_ALLOWED_FILES = frozenset(
    (
        "packages/niu-men-line-strategy/.gitignore",
        "packages/niu-men-line-strategy/README.md",
        "packages/niu-men-line-strategy/pyproject.toml",
        "packages/niu-men-line-strategy/schemas/research-snapshot.schema.json",
        "packages/niu-men-line-strategy/docs/README.md",
        "packages/niu-men-line-strategy/docs/a1-integration.md",
        "packages/niu-men-line-strategy/docs/dashboard-snapshot.md",
        "packages/niu-men-line-strategy/docs/data-contract.md",
        "packages/niu-men-line-strategy/docs/maintenance-and-quality.md",
        "packages/niu-men-line-strategy/docs/oos-stability-diagnostics.md",
        "packages/niu-men-line-strategy/docs/restricted-strategy-notes.md",
        "packages/niu-men-line-strategy/docs/portfolio-backtester-adapter.md",
        "packages/niu-men-line-strategy/docs/strategy-spec.md",
    )
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
        "apps/dashboard/wrangler.jsonc",
        "apps/dashboard/web/.gitignore",
        "apps/dashboard/web/index.html",
        "apps/dashboard/web/package-lock.json",
        "apps/dashboard/web/package.json",
        "apps/dashboard/web/playwright.config.mjs",
        "apps/dashboard/web/public/data.json",
        "apps/dashboard/web/public/rbreaker-research.json",
        "apps/dashboard/web/public/research.json",
        "apps/dashboard/web/tsconfig.json",
        "apps/dashboard/web/vite.config.ts",
    )
)

FORBIDDEN_TRACKED_PATH_PATTERNS = (
    re.compile(r"(?:^|/)data/raw(?:/|$)"),
    re.compile(r"(?:^|/)artifacts(?:/|$)"),
)

FORBIDDEN_CREDENTIAL_NAME_PATTERN = re.compile(
    r"(?:^\.env.*$|.*\b(?:credential|secret|token|password)\b.*|.*\.(?:pem|key|p12|pfx)$)",
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
    if any(pattern.search(relative) for pattern in FORBIDDEN_TRACKED_PATH_PATTERNS):
        return True
    name = relative.rsplit("/", 1)[-1]
    if name == ".env.example":
        return False
    return bool(FORBIDDEN_CREDENTIAL_NAME_PATTERN.fullmatch(name))


def is_allowed_tracked_file(relative: str) -> bool:
    """Return whether a tracked path is an M1 foundation or manifest path."""
    if is_forbidden_tracked_file(relative):
        return False
    return (
        relative in M1_FOUNDATION_TRACKED_FILES
        or relative in DASHBOARD_ALLOWED_FILES
        or relative in NIU_MEN_ALLOWED_FILES
        or relative in RESEARCH_CORE_ALLOWED_FILES
        or relative in MARKET_DATA_ALLOWED_FILES
        or relative.startswith(SUPERPOWERS_ALLOWED_DIRECTORY_PREFIXES)
        or relative in DOCUMENTATION_ALLOWED_FILES
        or relative.startswith(DOCUMENTATION_ALLOWED_DIRECTORY_PREFIXES)
        or relative.startswith(DASHBOARD_ALLOWED_DIRECTORY_PREFIXES)
        or relative.startswith(NIU_MEN_ALLOWED_DIRECTORY_PREFIXES)
        or relative.startswith(RESEARCH_CORE_ALLOWED_DIRECTORY_PREFIXES)
        or relative.startswith(MARKET_DATA_ALLOWED_DIRECTORY_PREFIXES)
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
