from pathlib import Path

from trading_research.data.config import (
    project_artifact_root,
    project_cache_root,
    project_data_root,
)


def test_project_data_root_defaults_to_user_data_directory(monkeypatch) -> None:
    monkeypatch.delenv("TRADING_RESEARCH_DATA_ROOT", raising=False)

    assert project_data_root() == Path.home() / "data" / "trading-research-dashboard"


def test_project_data_root_can_be_overridden(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRADING_RESEARCH_DATA_ROOT", str(tmp_path / "research-data"))

    assert project_data_root() == tmp_path / "research-data"


def test_project_data_subdirectories_are_stable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRADING_RESEARCH_DATA_ROOT", str(tmp_path))

    assert project_cache_root() == tmp_path / "cache"
    assert project_artifact_root() == tmp_path / "artifacts"
