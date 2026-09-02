"""Install a public research-platform publication into Dashboard static assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

PLATFORM_PUBLICATION_SCHEMA = "research.platform-publication.v1"
DASHBOARD_CONSUMER = "trading-research-dashboard"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _safe_relative_path(value: object) -> str:
    text = _required_text(value, "relative_path")
    if "\\" in text:
        raise ValueError("relative_path must use POSIX separators")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("relative_path must be a safe relative path")
    return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_mapping(value: object, *, index: int) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"artifacts[{index}] must be an object")
    artifact_id = _required_text(value.get("artifact_id"), f"artifacts[{index}].artifact_id")
    relative_path = _safe_relative_path(value.get("relative_path"))
    schema_version = _required_text(
        value.get("schema_version"), f"artifacts[{index}].schema_version"
    )
    sha256 = _required_text(value.get("sha256"), f"artifacts[{index}].sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise ValueError(f"artifacts[{index}].sha256 must be a lowercase SHA-256 digest")
    media_type = _required_text(value.get("media_type"), f"artifacts[{index}].media_type")
    audience = _required_text(value.get("audience"), f"artifacts[{index}].audience")
    if audience not in {"public", "internal"}:
        raise ValueError(f"artifacts[{index}].audience must be public or internal")
    consumers_raw = value.get("consumers")
    if not isinstance(consumers_raw, Sequence) or isinstance(
        consumers_raw, (str, bytes, bytearray)
    ):
        raise ValueError(f"artifacts[{index}].consumers must be a list")
    consumers = [_required_text(item, f"artifacts[{index}].consumers[]") for item in consumers_raw]
    if not consumers or len(set(consumers)) != len(consumers):
        raise ValueError(f"artifacts[{index}].consumers must be non-empty and unique")
    return {
        "artifact_id": artifact_id,
        "relative_path": relative_path,
        "schema_version": schema_version,
        "sha256": sha256,
        "media_type": media_type,
        "audience": audience,
        "consumers": consumers,
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"platform publication manifest not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid platform publication JSON: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("platform publication manifest must be a JSON object")
    schema_version = _required_text(payload.get("schema_version"), "schema_version")
    if schema_version != PLATFORM_PUBLICATION_SCHEMA:
        raise ValueError(f"unsupported platform publication schema {schema_version!r}")
    artifacts_raw = payload.get("artifacts")
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise ValueError("artifacts must be a non-empty list")
    artifacts = [_artifact_mapping(item, index=index) for index, item in enumerate(artifacts_raw)]
    ids = [item["artifact_id"] for item in artifacts]
    paths = [item["relative_path"] for item in artifacts]
    if len(set(ids)) != len(ids):
        raise ValueError("artifact_id values must be unique")
    if len(set(paths)) != len(paths):
        raise ValueError("relative_path values must be unique")
    return {
        "schema_version": schema_version,
        "generated_at": _required_text(payload.get("generated_at"), "generated_at"),
        "producer_repository": _required_text(
            payload.get("producer_repository"), "producer_repository"
        ),
        "producer_commit": _required_text(payload.get("producer_commit"), "producer_commit"),
        "run_id": _required_text(payload.get("run_id"), "run_id"),
        "artifacts": artifacts,
    }


def install_platform_publication(
    bundle_root: str | Path,
    public_root: str | Path,
) -> dict[str, Any]:
    """Validate a bundle and install only public Dashboard-targeted projections.

    Validation is completed before the current static projection is replaced, so
    a malformed or tampered bundle cannot partially overwrite the last good copy.
    The published manifest is filtered as well; internal artifact identities and
    paths never enter the public static site.
    """

    source_root = Path(bundle_root).expanduser().resolve()
    target_root = Path(public_root).expanduser().resolve()
    manifest = _load_manifest(source_root / "platform-publication.json")

    targeted = [
        artifact
        for artifact in manifest["artifacts"]
        if DASHBOARD_CONSUMER in artifact["consumers"]
    ]
    internal = [artifact["artifact_id"] for artifact in targeted if artifact["audience"] == "internal"]
    if internal:
        raise ValueError(
            "internal artifacts cannot be published to trading-research-dashboard: "
            + ", ".join(sorted(internal))
        )
    selected = [artifact for artifact in targeted if artifact["audience"] == "public"]
    if not selected:
        raise ValueError("platform publication contains no public Dashboard projection")

    verified: list[tuple[dict[str, Any], Path]] = []
    for artifact in selected:
        candidate = (source_root / artifact["relative_path"]).resolve()
        if candidate != source_root and source_root not in candidate.parents:
            raise ValueError(f"relative_path escapes bundle root: {artifact['artifact_id']}")
        if not candidate.is_file():
            raise FileNotFoundError(
                f"platform publication artifact missing: {artifact['artifact_id']} -> {candidate}"
            )
        actual = _sha256(candidate)
        if actual != artifact["sha256"]:
            raise ValueError(
                "platform publication SHA-256 mismatch for "
                f"{artifact['artifact_id']}: expected {artifact['sha256']}, got {actual}"
            )
        verified.append((artifact, candidate))

    target_root.mkdir(parents=True, exist_ok=True)
    platform_root = target_root / "platform"
    staging_root = target_root / ".platform-publication-staging"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True)
    try:
        for artifact, source in verified:
            destination = staging_root / artifact["relative_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        public_manifest = {
            "schema_version": manifest["schema_version"],
            "generated_at": manifest["generated_at"],
            "producer_repository": manifest["producer_repository"],
            "producer_commit": manifest["producer_commit"],
            "run_id": manifest["run_id"],
            "artifacts": [artifact for artifact, _ in verified],
        }
        manifest_temp = target_root / ".platform-publication.json.tmp"
        manifest_temp.write_text(
            json.dumps(public_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if platform_root.exists():
            shutil.rmtree(platform_root)
        staging_root.replace(platform_root)
        manifest_temp.replace(target_root / "platform-publication.json")
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)

    return {
        "schema_version": PLATFORM_PUBLICATION_SCHEMA,
        "run_id": manifest["run_id"],
        "producer_repository": manifest["producer_repository"],
        "producer_commit": manifest["producer_commit"],
        "artifact_count": len(verified),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install public research publication projections")
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--public-root", required=True, type=Path)
    args = parser.parse_args(argv)
    result = install_platform_publication(args.bundle_root, args.public_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
