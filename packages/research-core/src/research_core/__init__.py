"""Shared research contracts."""

from research_core.adapters import NIU_MEN_WIRE_VERSION, adapt_niu_men_v2
from research_core.agent_portfolio import (
    AGENT_PORTFOLIO_VERSION,
    load_agent_portfolio,
    validate_agent_portfolio,
    validate_target_weights,
)
from research_core.contextual import (
    CONDITIONAL_RESEARCH_VERSION,
    CONTEXTUAL_SNAPSHOT_VERSION,
    EVENT_STUDY_VERSION,
    MARKET_CONTEXT_VERSION,
    SETUP_EVENT_VERSION,
    load_contextual_snapshot,
    validate_conditional_research,
    validate_contextual_snapshot,
    validate_event_study,
    validate_market_context,
    validate_setup_event,
)
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
    "CONTEXTUAL_SNAPSHOT_VERSION",
    "CONDITIONAL_RESEARCH_VERSION",
    "AGENT_PORTFOLIO_VERSION",
    "EVENT_STUDY_VERSION",
    "MARKET_CONTEXT_VERSION",
    "NIU_MEN_WIRE_VERSION",
    "PROVENANCE_FIELDS",
    "SCHEMA_VERSION",
    "SETUP_EVENT_VERSION",
    "STRATEGY_SNAPSHOT_VERSION",
    "adapt_niu_men_v2",
    "load_agent_portfolio",
    "load_contextual_snapshot",
    "validate_conditional_research",
    "load_snapshot",
    "load_strategy_snapshot",
    "missing_provenance_fields",
    "provenance_complete",
    "validate_contextual_snapshot",
    "validate_event_study",
    "validate_market_context",
    "validate_provenance_consistency",
    "validate_setup_event",
    "validate_snapshot",
    "validate_strategy_snapshot",
    "validate_agent_portfolio",
    "validate_target_weights",
]
