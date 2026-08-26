import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_export_dashboard_snapshot import _write_snapshot_inputs

from scripts import publish_dashboard_snapshot as publish_module


def _run_publish(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "publish_dashboard_snapshot.py"),
            "--oos-json",
            str(tmp_path / "oos.json"),
            "--research-manifest",
            str(tmp_path / "research-manifest.json"),
            "--output",
            str(tmp_path / "research.json"),
            *extra,
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


def test_publish_dashboard_snapshot_writes_v2_output(tmp_path: Path) -> None:
    _write_snapshot_inputs(tmp_path)

    completed = _run_publish(tmp_path, "--snapshot-generated-at", "2026-08-25T10:15:00Z")

    assert completed.returncode == 0, completed.stderr
    snapshot = json.loads((tmp_path / "research.json").read_text(encoding="utf-8"))
    assert snapshot["schemaVersion"] == "niu_men.research_snapshot.v2"
    assert snapshot["generatedAt"] == "2026-08-25T10:15:00Z"


@pytest.mark.parametrize("missing_input", ["oos", "manifest"])
def test_publish_dashboard_snapshot_fails_before_output_when_input_is_missing(
    tmp_path: Path,
    missing_input: str,
) -> None:
    _write_snapshot_inputs(tmp_path)
    missing_path = (
        tmp_path / "oos.json" if missing_input == "oos" else tmp_path / "research-manifest.json"
    )
    missing_path.unlink()

    completed = _run_publish(tmp_path)

    assert completed.returncode != 0
    assert not (tmp_path / "research.json").exists()
    assert "不存在" in completed.stderr


def test_publish_dashboard_snapshot_rejects_empty_oos_rows(tmp_path: Path) -> None:
    _write_snapshot_inputs(tmp_path)
    columns = pd.read_csv(tmp_path / "folds.csv", nrows=0).columns
    pd.DataFrame(columns=columns).to_csv(tmp_path / "folds.csv", index=False)

    completed = _run_publish(tmp_path)

    assert completed.returncode != 0
    assert "OOS 记录为空" in completed.stderr
    assert not (tmp_path / "research.json").exists()


def test_publish_snapshot_rejects_schema_invalid_built_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_snapshot_inputs(tmp_path)
    monkeypatch.setattr(
        publish_module,
        "build_snapshot",
        lambda **_: {
            "schemaVersion": "niu_men.research_snapshot.v2",
            "generatedAt": "2026-08-25T10:15:00Z",
            "source": {},
            "mapping": {},
            "coverage": {},
            "walkForward": {},
            "variants": [],
            "executionConstraints": {},
            "quality": {"checks": {"oosRowsPresent": True}},
        },
    )

    with pytest.raises(ValueError, match="schema"):
        publish_module.publish_snapshot(
            oos_json=tmp_path / "oos.json",
            research_manifest=tmp_path / "research-manifest.json",
            output=tmp_path / "research.json",
        )

    assert not (tmp_path / "research.json").exists()


def test_publication_workflow_uses_reviewable_dashboard_handoff() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workflow = (repo_root / ".github" / "workflows" / "publish-dashboard-snapshot.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch" in workflow
    assert "oos_json" in workflow
    assert "research_manifest" in workflow
    assert "dashboard_repository" in workflow
    assert "publish_dashboard_snapshot.py" in workflow
    assert "schemas/research-snapshot.schema.json" in workflow
    assert "tests/fixtures/research_snapshot" in workflow
    assert "dashboard/schemas/research-snapshot.schema.json" in workflow
    assert "dashboard/tests/fixtures/research_snapshot" in workflow
    assert "web/public/research.json" in workflow
    assert "peter-evans/create-pull-request" in workflow
