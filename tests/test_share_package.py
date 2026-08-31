from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.package_share import build_share_package


def test_share_package_contains_env_example_and_excludes_credentials(tmp_path: Path) -> None:
    output = tmp_path / "trading-research-dashboard-share.zip"

    manifest = build_share_package(output)

    assert output.exists()
    assert ".env.example" in manifest["files"]
    assert all(not name.endswith("/.env") and name != ".env" for name in manifest["files"])
    assert all("node_modules/" not in name for name in manifest["files"])
    assert all("test-results/" not in name for name in manifest["files"])
    assert all("data/raw/" not in name for name in manifest["files"])
    assert all(not name.endswith(".coverage") for name in manifest["files"])


def test_share_package_rejects_repository_output_path() -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        build_share_package(Path(__file__).parents[1] / "share.zip")


def test_share_package_manifest_is_json_safe(tmp_path: Path) -> None:
    output = tmp_path / "share.zip"

    manifest = build_share_package(output)

    json.dumps(manifest)
    assert all("secret" not in name.lower() for name in manifest["files"])


def test_share_package_contains_runtime_code_workflows_and_dashboard_snapshots(tmp_path: Path) -> None:
    manifest = build_share_package(tmp_path / "share.zip")

    files = set(manifest["files"])
    assert "apps/dashboard/src/trading_research/data/config.py" in files
    assert ".github/workflows/dashboard-report.yml" in files
    assert "apps/dashboard/web/public/data.json" in files
    assert "apps/dashboard/web/public/research.json" in files
    assert "apps/dashboard/web/public/rbreaker-research.json" in files
    assert "apps/dashboard/web/public/ict-liquidity-reclaim-research.json" in files


def test_share_package_manifest_describes_external_data_sources(tmp_path: Path) -> None:
    manifest = build_share_package(tmp_path / "share.zip")

    assert manifest["format"] == "trading-research-dashboard.share.v2"
    assert manifest["externalDataSources"] == [
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
    ]
