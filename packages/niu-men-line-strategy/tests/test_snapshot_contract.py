import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "research_snapshot"


def test_valid_v2_fixture_matches_schema() -> None:
    assert (FIXTURE_ROOT / "valid_v2.json").is_file()
    from scripts.snapshot_contract import load_snapshot

    snapshot = load_snapshot(FIXTURE_ROOT / "valid_v2.json")

    assert snapshot["schemaVersion"] == "niu_men.research_snapshot.v2"
    assert snapshot["quality"]["status"] == "pass"


def test_warning_v2_fixture_matches_schema_without_inventing_provenance() -> None:
    from scripts.snapshot_contract import load_snapshot

    snapshot = load_snapshot(FIXTURE_ROOT / "warning_v2.json")

    assert snapshot["quality"]["status"] == "warning"
    assert snapshot["quality"]["checks"]["provenanceComplete"] is False
    assert snapshot["source"]["researchCommit"] is None


def test_missing_required_fixture_is_rejected() -> None:
    from scripts.snapshot_contract import load_snapshot

    with pytest.raises(ValueError, match="schema"):
        load_snapshot(FIXTURE_ROOT / "invalid_missing_required.json")


def test_unsupported_version_fixture_is_rejected() -> None:
    from scripts.snapshot_contract import load_snapshot

    with pytest.raises(ValueError, match="schema"):
        load_snapshot(FIXTURE_ROOT / "unsupported_version.json")


def test_fixture_files_are_json_documents() -> None:
    for path in FIXTURE_ROOT.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
