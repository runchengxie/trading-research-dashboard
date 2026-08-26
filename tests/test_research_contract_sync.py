import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SCHEMA = (
    ROOT / "packages/research-core/src/research_core/schemas/research-snapshot.schema.json"
)
CANONICAL_FIXTURES = ROOT / "packages/research-core/tests/fixtures/research_snapshot"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_mirrors_match_canonical() -> None:
    expected = read_json(CANONICAL_SCHEMA)
    mirrors = (
        ROOT / "schemas/research-snapshot.schema.json",
        ROOT / "apps/dashboard/schemas/research-snapshot.schema.json",
        ROOT / "packages/niu-men-line-strategy/schemas/research-snapshot.schema.json",
    )
    for mirror in mirrors:
        assert read_json(mirror) == expected, mirror


def test_fixture_mirrors_match_canonical() -> None:
    for name in (
        "valid_v2.json",
        "warning_v2.json",
        "invalid_missing_required.json",
        "unsupported_version.json",
    ):
        expected = read_json(CANONICAL_FIXTURES / name)
        mirrors = (
            ROOT / "apps/dashboard/tests/fixtures/research_snapshot" / name,
            ROOT / "packages/niu-men-line-strategy/tests/fixtures/research_snapshot" / name,
        )
        for mirror in mirrors:
            assert read_json(mirror) == expected, mirror
