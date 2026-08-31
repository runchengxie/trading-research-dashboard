"""Project-owned data locations for Dashboard runtime and research outputs."""

from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT_ENV = "TRADING_RESEARCH_DATA_ROOT"
DEFAULT_DATA_ROOT = Path.home() / "data" / "trading-research-dashboard"


def project_data_root() -> Path:
    """Return the project data root, honoring the process environment."""

    raw = os.getenv(DATA_ROOT_ENV, "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_DATA_ROOT


def project_cache_root() -> Path:
    return project_data_root() / "cache"


def project_artifact_root() -> Path:
    return project_data_root() / "artifacts"
