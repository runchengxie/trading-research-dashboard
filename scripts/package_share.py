"""Build a credential-safe, self-contained source bundle for private sharing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_FILES = (
    "README.md",
    ".env.example",
    ".gitignore",
    "pyproject.toml",
    "uv.lock",
    "AGENTS.md",
)
INCLUDE_DIRS = (
    ".github",
    "apps/dashboard",
    "apps/market-data-service",
    "packages",
    "docs",
    "scripts",
    "schemas",
    "tests",
)
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "playwright-report",
    "test-results",
    "out",
    "artifacts",
}
EXCLUDED_RELATIVE_PREFIXES = {
    Path("data"),
    Path("apps/dashboard/data"),
    Path("packages/niu-men-line-strategy/data"),
}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
STATIC_DASHBOARD_FILES = (
    "apps/dashboard/web/public/data.json",
    "apps/dashboard/web/public/research.json",
    "apps/dashboard/web/public/rbreaker-research.json",
    "apps/dashboard/web/public/ict-liquidity-reclaim-research.json",
)
EXTERNAL_DATA_SOURCES = (
    {
        "name": "market-data-platform",
        "included": False,
        "environmentVariable": "MARKET_DATA_PLATFORM_ROOT",
    },
    {
        "name": "etf-minute-fetcher",
        "included": False,
        "environmentVariable": "ETF_MINUTE_DATA_ROOT",
    },
)


def _is_safe_relative(path: Path) -> bool:
    parts = set(path.parts)
    name = path.name.lower()
    return (
        not any(path == prefix or prefix in path.parents for prefix in EXCLUDED_RELATIVE_PREFIXES)
        and
        not parts.intersection(EXCLUDED_PARTS)
        and name != ".coverage"
        and name not in SECRET_NAMES
        and not (name.startswith(".env.") and name != ".env.example")
        and not name.endswith(SECRET_SUFFIXES)
    )


def _files_to_include() -> list[Path]:
    candidates = [ROOT / relative for relative in INCLUDE_FILES]
    for directory in INCLUDE_DIRS:
        candidates.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    relative = sorted(
        path.relative_to(ROOT) for path in candidates if path.is_file() and _is_safe_relative(path.relative_to(ROOT))
    )
    return relative


def build_share_package(output: Path) -> dict[str, object]:
    output = output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("share package output must be outside the repository")
    output.parent.mkdir(parents=True, exist_ok=True)

    files = _files_to_include()
    manifest: dict[str, object] = {
        "format": "trading-research-dashboard.share.v2",
        "credentialsIncluded": False,
        "contents": {
            "sourceCode": True,
            "dashboardStaticData": [
                path for path in STATIC_DASHBOARD_FILES if path in {item.as_posix() for item in files}
            ],
        },
        "externalDataSources": [dict(source) for source in EXTERNAL_DATA_SOURCES],
        "files": [path.as_posix() for path in files],
        "sha256": {
            path.as_posix(): hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in files
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(ROOT / path, path.as_posix())
        archive.writestr("SHARE-MANIFEST.json", manifest_bytes)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a credential-safe private share archive")
    parser.add_argument("--output", type=Path, required=True, help="zip path outside this repository")
    args = parser.parse_args()
    manifest = build_share_package(args.output)
    print(f"Created {args.output} with {len(manifest['files'])} files; credentialsIncluded=false")


if __name__ == "__main__":
    main()
