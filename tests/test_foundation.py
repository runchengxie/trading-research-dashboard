from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


@pytest.mark.parametrize(
    ("relative_path", "contents"),
    (
        ("apps/dashboard/app.py", "print('Dashboard implementation')\n"),
        ("artifacts/oos/results.csv", "date,pnl\n2026-08-26,1\n"),
        (".env", "MARKET_DATA_TOKEN=secret\n"),
    ),
)
def test_tracked_file_outside_m0_allowlist_is_reported(
    tmp_path: Path, relative_path: str, contents: str
) -> None:
    """Reject source, OOS output, and credential-like files during M0."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    candidate = tmp_path / relative_path
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(contents, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", relative_path], check=True
    )

    errors = validate_foundation(tmp_path)

    assert f"tracked file is not allowed during M0: {relative_path}" in errors
