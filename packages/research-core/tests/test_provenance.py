import copy
import json
from pathlib import Path

import pytest

from research_core.provenance import (
    missing_provenance_fields,
    provenance_complete,
    validate_provenance_consistency,
)

FIXTURES = Path(__file__).parent / "fixtures" / "research_snapshot"


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_v2_has_complete_provenance() -> None:
    snapshot = read_fixture("valid_v2.json")
    assert missing_provenance_fields(snapshot) == ()
    assert provenance_complete(snapshot) is True
    validate_provenance_consistency(snapshot)


def test_warning_v2_reports_missing_provenance() -> None:
    snapshot = read_fixture("warning_v2.json")
    assert missing_provenance_fields(snapshot) == (
        "source.researchCommit",
        "source.dataPlatformManifest.schemaVersion",
        "source.dataPlatformManifest.generatedAt",
    )
    assert provenance_complete(snapshot) is False
    validate_provenance_consistency(snapshot)


def test_declared_complete_must_match_actual_fields() -> None:
    snapshot = read_fixture("warning_v2.json")
    snapshot["quality"]["checks"]["provenanceComplete"] = True
    with pytest.raises(ValueError, match="provenanceComplete"):
        validate_provenance_consistency(snapshot)


def test_incomplete_provenance_requires_warning_status() -> None:
    snapshot = read_fixture("warning_v2.json")
    snapshot["quality"]["status"] = "pass"
    with pytest.raises(ValueError, match="quality.status"):
        validate_provenance_consistency(snapshot)


def test_empty_string_counts_as_missing() -> None:
    snapshot = copy.deepcopy(read_fixture("valid_v2.json"))
    snapshot["source"]["researchCommit"] = ""
    assert provenance_complete(snapshot) is False
