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
