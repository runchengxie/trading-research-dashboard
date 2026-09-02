from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


SCRIPT = Path("scripts/publish_platform_publication.py").resolve()


def _load_publisher() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dashboard_platform_publisher", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_requires_default_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = _load_publisher()

    def fake_run(command: list[str], **_: object) -> str:
        if command[:3] == ["gh", "repo", "view"]:
            return "main"
        if command == ["git", "branch", "--show-current"]:
            return "feat/not-publication-base"
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(publisher, "_run", fake_run)

    with pytest.raises(SystemExit, match="wrong base branch"):
        publisher._preflight_update_pr()


def test_preflight_rejects_dirty_tree_before_install(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = _load_publisher()

    def fake_run(command: list[str], **_: object) -> str:
        if command[:3] == ["gh", "repo", "view"]:
            return "main"
        if command == ["git", "branch", "--show-current"]:
            return "main"
        if command == ["git", "status", "--porcelain"]:
            return " M apps/dashboard/web/public/platform-publication.json"
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(publisher, "_run", fake_run)

    with pytest.raises(SystemExit, match="dirty working tree"):
        publisher._preflight_update_pr()


def test_preflight_returns_clean_publication_base(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = _load_publisher()

    def fake_run(command: list[str], **_: object) -> str:
        if command[:3] == ["gh", "repo", "view"]:
            return "main"
        if command == ["git", "branch", "--show-current"]:
            return "main"
        if command == ["git", "status", "--porcelain"]:
            return ""
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(publisher, "_run", fake_run)

    assert publisher._preflight_update_pr() == "main"
