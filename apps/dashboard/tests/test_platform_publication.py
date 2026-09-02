from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from trading_research.platform_publication import install_platform_publication


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle(root: Path, *, internal_for_dashboard: bool = False) -> Path:
    evidence = root / "strategies" / "dailywatch20.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"status":"pass"}', encoding="utf-8")
    intel = root / "intel" / "digest.json"
    intel.parent.mkdir(parents=True)
    intel.write_text('{"headline":"internal"}', encoding="utf-8")
    manifest = {
        "schema_version": "research.platform-publication.v1",
        "generated_at": "2026-09-02T05:20:00+00:00",
        "producer_repository": "runchengxie/research-workspace",
        "producer_commit": "abc123",
        "run_id": "run-1",
        "artifacts": [
            {
                "artifact_id": "strategy.dailywatch20.evidence",
                "relative_path": "strategies/dailywatch20.json",
                "schema_version": "strategy.evidence.v1",
                "sha256": _sha256(evidence),
                "media_type": "application/json",
                "audience": "public",
                "consumers": ["trading-research-dashboard", "market-intel"],
            },
            {
                "artifact_id": "intel.digest",
                "relative_path": "intel/digest.json",
                "schema_version": "intel.digest.v1",
                "sha256": _sha256(intel),
                "media_type": "application/json",
                "audience": "internal",
                "consumers": [
                    "trading-research-dashboard" if internal_for_dashboard else "market-intel"
                ],
            },
        ],
    }
    manifest_path = root / "platform-publication.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_installer_copies_only_public_dashboard_projection(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _bundle(bundle_root)
    public_root = tmp_path / "public"

    result = install_platform_publication(bundle_root, public_root)

    assert result["artifact_count"] == 1
    assert (public_root / "platform-publication.json").is_file()
    assert (public_root / "platform" / "strategies" / "dailywatch20.json").read_text() == (
        '{"status":"pass"}'
    )
    assert not (public_root / "platform" / "intel" / "digest.json").exists()


def test_installer_rejects_internal_artifact_targeted_at_dashboard(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _bundle(bundle_root, internal_for_dashboard=True)

    with pytest.raises(ValueError, match="internal"):
        install_platform_publication(bundle_root, tmp_path / "public")


def test_installer_rejects_tampered_projection(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _bundle(bundle_root)
    projection = bundle_root / "strategies" / "dailywatch20.json"
    projection.write_text('{"status":"tampered"}', encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        install_platform_publication(bundle_root, tmp_path / "public")


def test_installer_rejects_path_traversal(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    manifest_path = _bundle(bundle_root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["relative_path"] = "../secret.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="relative_path"):
        install_platform_publication(bundle_root, tmp_path / "public")


def test_installer_rejects_bundle_without_public_dashboard_projection(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    manifest_path = _bundle(bundle_root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["consumers"] = ["market-intel"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="no public Dashboard projection"):
        install_platform_publication(bundle_root, tmp_path / "public")
