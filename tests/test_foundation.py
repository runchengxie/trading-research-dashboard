from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_foundation import validate_foundation


def test_current_repository_has_a_complete_foundation() -> None:
    root = Path(__file__).resolve().parents[1]

    assert validate_foundation(root) == []


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/migration/README.md",
        "docs/migration/dashboard-import.md",
        "uv.lock",
    ),
)
def test_complete_foundation_reports_deleted_required_file(
    tmp_path: Path, relative_path: str
) -> None:
    root = Path(__file__).resolve().parents[1]
    foundation = tmp_path / "foundation"
    shutil.copytree(
        root,
        foundation,
        ignore=shutil.ignore_patterns(".git", ".superpowers", ".venv", "__pycache__"),
    )
    (foundation / relative_path).unlink()

    errors = validate_foundation(foundation)

    assert f"required file missing: {relative_path}" in errors


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


def test_ignored_dependency_documentation_is_not_scanned_for_placeholders(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    dependency_readme = tmp_path / "node_modules" / "dependency" / "README.md"
    dependency_readme.parent.mkdir(parents=True)
    dependency_readme.write_text("TODO: dependency documentation\n", encoding="utf-8")

    errors = validate_foundation(tmp_path)

    assert not any(
        str(dependency_readme.relative_to(tmp_path)) in error for error in errors
    )


@pytest.mark.parametrize(
    ("relative_path", "contents", "is_allowed"),
    (
        (
            "apps/dashboard/src/trading_research/dashboard/astock_tech.py",
            "print('Dashboard implementation')\n",
            True,
        ),
        ("apps/dashboard/web/src/App.tsx", "export default null\n", True),
        ("apps/dashboard/data/raw/example.csv", "date,pnl\n2026-08-26,1\n", False),
        ("apps/dashboard/web/data/raw/example.csv", "date,pnl\n2026-08-26,1\n", False),
        ("apps/dashboard/web/public/research.json", "{}\n", False),
        ("apps/dashboard/web/public/generated-research.json", "{}\n", False),
        ("apps/dashboard/web/artifacts/results.json", "{}\n", False),
        ("apps/dashboard/.env", "MARKET_DATA_TOKEN=secret\n", False),
        ("apps/dashboard/web/src/.env.production", "MARKET_DATA_TOKEN=secret\n", False),
        ("packages/niu-men-line-strategy/src/placeholder.py", "pass\n", False),
        ("artifacts/oos/results.csv", "date,pnl\n2026-08-26,1\n", False),
        (".env", "MARKET_DATA_TOKEN=secret\n", False),
    ),
)
def test_tracked_file_respects_the_m1_boundary(
    tmp_path: Path, relative_path: str, contents: str, is_allowed: bool
) -> None:
    """Allow manifest paths and reject protected or unrelated tracked files."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    candidate = tmp_path / relative_path
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(contents, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-f", "--", relative_path], check=True
    )

    errors = validate_foundation(tmp_path)

    boundary_errors = [
        error
        for error in errors
        if error.startswith("tracked file is not allowed during")
        and error.endswith(f": {relative_path}")
    ]
    if is_allowed:
        assert boundary_errors == []
    else:
        assert boundary_errors == [
            f"tracked file is not allowed during M1: {relative_path}"
        ]


def test_tracked_gitlink_is_reported_as_a_m1_boundary_violation(tmp_path: Path) -> None:
    """Reject a gitlink even when its path resembles a Dashboard directory."""
    relative_path = "apps/dashboard/src/linked-source"
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "update-index",
            "--add",
            "--cacheinfo",
            "160000",
            "0123456789012345678901234567890123456789",
            relative_path,
        ],
        check=True,
    )

    errors = validate_foundation(tmp_path)

    assert f"gitlink is not allowed during M1: {relative_path}" in errors
