"""Compatibility wrapper for canonical snapshot validation in research-core.

The canonical schema, fixtures and validation semantics live in
``packages/research-core``. This module re-exports the shared API so existing
callers of ``scripts.snapshot_contract`` keep working unchanged.
"""

from __future__ import annotations

from pathlib import Path

from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "research-snapshot.schema.json"

__all__ = ["SCHEMA_PATH", "SCHEMA_VERSION", "load_snapshot", "validate_snapshot"]
