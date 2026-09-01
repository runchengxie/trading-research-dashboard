from __future__ import annotations

import json
from pathlib import Path

from .app import create_app


def render_openapi_json() -> str:
    return json.dumps(
        create_app().openapi(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_openapi_json(output: str | Path) -> Path:
    path = Path(output)
    path.write_text(render_openapi_json(), encoding="utf-8")
    return path
