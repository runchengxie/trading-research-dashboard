import json
from pathlib import Path

import pytest

sys_path = str(Path(__file__).resolve().parents[1])
if sys_path not in __import__("sys").path:
    import sys

    sys.path.insert(0, sys_path)

from scripts.publish_research_snapshot import publish

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "packages" / "research-core" / "tests" / "fixtures" / "research_snapshot"
DASHBOARD_PUBLIC = REPO_ROOT / "apps" / "dashboard" / "web" / "public"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_dashboard(tmp_path: Path, research: bytes | None) -> tuple[Path, Path]:
    public = tmp_path / "public"
    public.mkdir()
    data_path = public / "data.json"
    data_path.write_text(
        '{"generatedAt":"2026-08-26T00:00:00Z","stocks":[{"code":"sz300246"}]}',
        encoding="utf-8",
    )
    target = public / "research.json"
    if research is not None:
        target.write_bytes(research)
    return data_path, target


def test_missing_input_fails_without_touching_target(tmp_path: Path) -> None:
    data_path, target = make_dashboard(tmp_path, b'{"schemaVersion":"niu_men.research_snapshot.v2"}\n')
    missing = tmp_path / "nope.json"

    with pytest.raises(SystemExit, match="snapshot input is missing"):
        publish(missing, data_path=data_path, target=target)

    assert target.read_bytes() == b'{"schemaVersion":"niu_men.research_snapshot.v2"}\n'


def test_invalid_schema_is_rejected_and_previous_snapshot_preserved(tmp_path: Path) -> None:
    previous = b'{"previous": true}\n'
    data_path, target = make_dashboard(tmp_path, previous)
    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        (FIXTURES / "invalid_missing_required.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="snapshot schema validation failed"):
        publish(candidate, data_path=data_path, target=target)

    assert target.read_bytes() == previous


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ({"quality": {"status": "pass", "checks": {"provenanceComplete": True}}}, "provenanceComplete"),
        ({"quality": {"status": "pass"}}, None),
    ),
)
def test_inconsistent_provenance_is_rejected_before_write(
    tmp_path: Path, mutation: dict, message: str | None
) -> None:
    previous = b'{"previous": true}\n'
    data_path, target = make_dashboard(tmp_path, previous)
    payload = read_json(FIXTURES / "warning_v2.json")
    payload.update(mutation)
    if message is None and mutation["quality"] == {"status": "pass"}:
        # warning fixture has incomplete provenance; forcing pass status must fail.
        pass
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        publish(candidate, data_path=data_path, target=target)

    assert target.read_bytes() == previous


def test_valid_snapshot_is_published_atomically(tmp_path: Path) -> None:
    data_path, target = make_dashboard(tmp_path, b'{"previous": true}\n')
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes((FIXTURES / "valid_v2.json").read_bytes())

    published = publish(candidate, data_path=data_path, target=target)

    assert published == target
    assert read_json(target) == read_json(candidate)


def test_static_validation_failure_restores_previous_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = b'{"previous": true}\n'
    data_path, target = make_dashboard(tmp_path, previous)
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes((FIXTURES / "valid_v2.json").read_bytes())

    def broken_validate(*args, **kwargs):
        raise ValueError("static validation exploded")

    monkeypatch.setattr(
        "scripts.publish_research_snapshot.validate_dashboard_snapshots", broken_validate
    )

    with pytest.raises(ValueError, match="static validation exploded"):
        publish(candidate, data_path=data_path, target=target)

    assert target.read_bytes() == previous


def test_committed_real_snapshots_still_publish_cleanly(tmp_path: Path) -> None:
    """The real committed Dashboard snapshot passes the publisher unchanged."""

    data_path = DASHBOARD_PUBLIC / "data.json"
    current = DASHBOARD_PUBLIC / "research.json"
    target = tmp_path / "public" / "research.json"
    target.parent.mkdir()

    published = publish(current, data_path=data_path, target=target)

    assert read_json(published) == read_json(current)
