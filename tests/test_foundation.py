from pathlib import Path

from scripts.check_foundation import validate_foundation


def test_current_repository_has_a_complete_foundation() -> None:
    root = Path(__file__).resolve().parents[1]

    assert validate_foundation(root) == []


def test_missing_required_file_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")

    errors = validate_foundation(tmp_path)

    assert any("AGENTS.md" in error for error in errors)


def test_forbidden_external_project_directory_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# guidance\n", encoding="utf-8")
    (tmp_path / "research-workspace").mkdir()

    errors = validate_foundation(tmp_path)

    assert any("research-workspace" in error for error in errors)


def test_placeholder_markers_in_documentation_are_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# guidance\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.md").write_text("TODO: fill this\n", encoding="utf-8")

    errors = validate_foundation(tmp_path)

    assert any("placeholder" in error.lower() for error in errors)
