import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from write_runtime_manifest import build_runtime_manifest


def test_shadow_runtime_manifest_records_commit_and_data_date() -> None:
    manifest = build_runtime_manifest(
        data={"generatedAt": "2026-08-27", "stocks": [{"code": "sz300246"}]},
        mode="shadow",
        commit="abc123",
        run_id="456",
        public_url=None,
        now=datetime(2026, 8, 27, 1, 20, tzinfo=UTC),
    )

    assert manifest == {
        "schemaVersion": "trading_research.runtime_manifest.v1",
        "mode": "shadow",
        "commit": "abc123",
        "workflowRunId": "456",
        "dataGeneratedAt": "2026-08-27",
        "createdAt": "2026-08-27T01:20:00+00:00",
        "publicUrl": None,
    }


def test_authoritative_runtime_manifest_requires_public_url() -> None:
    with pytest.raises(ValueError, match="public URL"):
        build_runtime_manifest(
            data={"generatedAt": "2026-08-27", "stocks": [{"code": "sz300246"}]},
            mode="authoritative",
            commit="abc123",
            run_id=None,
            public_url=None,
        )


def test_runtime_manifest_rejects_invalid_mode_or_missing_data_date() -> None:
    with pytest.raises(ValueError, match="mode"):
        build_runtime_manifest(
            data={"generatedAt": "2026-08-27", "stocks": [{"code": "sz300246"}]},
            mode="production",
            commit="abc123",
            run_id=None,
            public_url=None,
        )
    with pytest.raises(ValueError, match="generatedAt"):
        build_runtime_manifest(
            data={"stocks": [{"code": "sz300246"}]},
            mode="shadow",
            commit="abc123",
            run_id=None,
            public_url=None,
        )
