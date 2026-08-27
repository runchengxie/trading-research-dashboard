from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_SYMBOL_PATTERN = re.compile(r"^(?P<market>sh|sz|bj)[.?](?P<code>\d{6})$|^(?P<plain>sh|sz|bj)\d{6}$", re.I)
_REQUIRED_MANIFEST_FIELDS = {
    "schemaVersion",
    "symbol",
    "dataStart",
    "dataEnd",
    "barInterval",
    "source",
    "generatedAt",
    "producerCommit",
    "previousDay",
    "files",
}
_BAR_COLUMNS = {
    "open": "开盘",
    "high": "最高",
    "low": "最低",
    "close": "收盘",
    "volume": "成交量",
}


@dataclass(frozen=True, slots=True)
class ArtifactFile:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    root: Path
    symbol: str
    data_start: str
    data_end: str
    bar_interval: str
    source: str
    generated_at: str
    producer_commit: str
    previous_day: tuple[float, float, float]
    files: tuple[ArtifactFile, ...]


def _normalize_symbol(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ValueError("symbol must be a string")
    value = raw.strip().lower()
    match = _SYMBOL_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"invalid symbol: {raw!r}")
    if match.group("plain"):
        return value
    return f"{match.group('market')}{match.group('code')}"


def _contained_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not relative.startswith("bars/"):
        raise ValueError(f"invalid artifact path: {relative!r}")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if resolved_root not in resolved.parents:
        raise ValueError(f"artifact path escapes root: {relative!r}")
    return resolved


def load_artifact(root: Path) -> ArtifactManifest:
    root = Path(root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("artifact manifest.json is missing")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid artifact manifest JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("artifact manifest must be an object")
    missing = _REQUIRED_MANIFEST_FIELDS - payload.keys()
    if missing:
        raise ValueError(f"manifest missing fields: {', '.join(sorted(missing))}")
    if payload["schemaVersion"] != "trading_research.rbreaker_input.v1":
        raise ValueError("unsupported artifact schemaVersion")
    if payload["barInterval"] != "1m":
        raise ValueError("barInterval must be 1m")
    symbol = _normalize_symbol(payload["symbol"])
    previous_day = payload["previousDay"]
    if not isinstance(previous_day, dict) or not {"high", "low", "close"} <= previous_day.keys():
        raise ValueError("previousDay must contain high, low, and close")
    try:
        previous = (
            float(previous_day["high"]),
            float(previous_day["low"]),
            float(previous_day["close"]),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("previousDay values must be numbers") from exc
    if any(value <= 0 for value in previous):
        raise ValueError("previousDay values must be positive")

    raw_files = payload["files"]
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("manifest files must be a non-empty list")
    files: list[ArtifactFile] = []
    for item in raw_files:
        if not isinstance(item, dict) or not {"path", "bytes", "sha256"} <= item.keys():
            raise ValueError("each manifest file needs path, bytes, and sha256")
        relative = item["path"]
        if not isinstance(relative, str) or not relative.endswith(".parquet"):
            raise ValueError(f"invalid artifact path: {relative!r}")
        target = _contained_path(root, relative)
        if not target.is_file():
            raise ValueError(f"artifact file is missing: {relative}")
        expected_bytes = int(item["bytes"])
        actual_bytes = target.stat().st_size
        if actual_bytes != expected_bytes:
            raise ValueError(f"byte size mismatch for {relative}")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {relative}")
        files.append(ArtifactFile(relative, expected_bytes, digest))
    tracked = {item.path for item in files}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != tracked:
        raise ValueError("artifact contains files not declared in manifest")
    return ArtifactManifest(
        root=root,
        symbol=symbol,
        data_start=str(payload["dataStart"]),
        data_end=str(payload["dataEnd"]),
        bar_interval="1m",
        source=str(payload["source"]),
        generated_at=str(payload["generatedAt"]),
        producer_commit=str(payload["producerCommit"]),
        previous_day=previous,
        files=tuple(files),
    )


def load_minute_bars(manifest: ArtifactManifest) -> pd.DataFrame:
    if len(manifest.files) != 1:
        raise ValueError("R-Breaker currently requires exactly one bars file")
    frame = pd.read_parquet(manifest.root / manifest.files[0].path)
    if frame.empty:
        raise ValueError("minute bars are empty")
    required = {"datetime", *_BAR_COLUMNS}
    if not required <= set(frame.columns):
        missing = required - set(frame.columns)
        raise ValueError(f"minute bars missing columns: {', '.join(sorted(missing))}")
    frame = frame[["datetime", *_BAR_COLUMNS]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    if frame["datetime"].isna().any():
        raise ValueError("minute bars contain invalid datetime")
    if frame["datetime"].duplicated().any():
        raise ValueError("minute bars contain duplicate datetime")
    for column in _BAR_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[list(_BAR_COLUMNS)].isna().any().any():
        raise ValueError("minute bars contain null numeric values")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("minute bar prices must be positive")
    frame = frame.sort_values("datetime").set_index("datetime")
    frame.index.name = "datetime"
    return frame.rename(columns=_BAR_COLUMNS)
