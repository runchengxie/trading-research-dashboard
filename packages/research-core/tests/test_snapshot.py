import json
from pathlib import Path

import pytest

from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "research_snapshot"


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_schema_version_is_v2() -> None:
    assert SCHEMA_VERSION == "niu_men.research_snapshot.v2"


def test_valid_v2_passes() -> None:
    validate_snapshot(read_fixture("valid_v2.json"))


def test_warning_v2_is_structurally_valid() -> None:
    validate_snapshot(read_fixture("warning_v2.json"))


def test_missing_required_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_snapshot(read_fixture("invalid_missing_required.json"))


def test_unsupported_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="schemaVersion"):
        validate_snapshot(read_fixture("unsupported_version.json"))


def test_non_mapping_root_is_rejected() -> None:
    with pytest.raises(TypeError, match="root must be an object"):
        validate_snapshot([])  # type: ignore[arg-type]


def test_load_snapshot_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_snapshot(path)
