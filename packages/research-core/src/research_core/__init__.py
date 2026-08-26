"""Shared research contracts."""

from research_core.adapters import NIU_MEN_WIRE_VERSION, adapt_niu_men_v2
from research_core.provenance import (
    PROVENANCE_FIELDS,
    missing_provenance_fields,
    provenance_complete,
    validate_provenance_consistency,
)
from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot
from research_core.strategy_snapshot import (
    STRATEGY_SNAPSHOT_VERSION,
    load_strategy_snapshot,
    validate_strategy_snapshot,
)

__all__ = [
    "NIU_MEN_WIRE_VERSION",
    "PROVENANCE_FIELDS",
    "SCHEMA_VERSION",
    "STRATEGY_SNAPSHOT_VERSION",
    "adapt_niu_men_v2",
    "load_snapshot",
    "load_strategy_snapshot",
    "missing_provenance_fields",
    "provenance_complete",
    "validate_provenance_consistency",
    "validate_snapshot",
    "validate_strategy_snapshot",
]
