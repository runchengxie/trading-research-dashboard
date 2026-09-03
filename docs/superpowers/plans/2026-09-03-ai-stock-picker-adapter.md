# AI Stock Picker Canonical Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert an owner-validated `ai-stock-picker` selection plus a matching content-bound validation receipt into canonical `agent_run.v1` and `research_evidence.v1` records.

**Architecture:** Add one pure Dashboard app adapter that parses selection JSON bytes, validates only the external handshake fields needed for safe projection, recomputes the selection digest, verifies the owner receipt identity, maps conservative lineage/PIT limitations, then delegates final wire validation to `research-core`. No network calls, wall clock reads, provider execution, experiment generation, or eval generation.

**Tech Stack:** Python 3.11+, stdlib `json/hashlib`, `research-core`, `pytest`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-09-03-ai-stock-picker-adapter-design.md`

## Global Constraints

- Adapter lives in `apps/dashboard`, not `research-core`.
- Do not import the `ai-stock-picker` Python package.
- Accept only validation receipt schema `1.0.0` with `current_full` validation in v1.
- Recompute `selection_sha256`; never trust `valid=true` alone.
- Preserve `strict_point_in_time`, `eligible_as_oos_evidence`, assurance and all producer limitations without upgrade.
- Do not invent `startedAt`, token usage, cost, latency, task count or iterations.
- `adapted_at` is explicit input; no system clock access.
- Return only canonical `agent_run.v1` and `research_evidence.v1`.
- Keep this PR Draft until producer PR #109 is locally verified and merged.

---

### Task 1: Define successful canonical projection

**Files:**
- Create: `apps/dashboard/tests/test_ai_stock_picker_adapter.py`
- Create: `apps/dashboard/src/trading_research/ai_stock_picker_adapter.py`

**Interfaces:**
- Produces: `adapt_ai_stock_picker_selection(selection_bytes: bytes, validation_receipt: Mapping[str, Any], *, adapted_at: str) -> tuple[dict[str, Any], dict[str, Any]]`

- [ ] Write a valid current `ai_stock_selection` fixture and matching receipt fixture.
- [ ] Assert the adapter is initially missing/failing.
- [ ] Implement minimal parser, digest comparison and mapping.
- [ ] Assert returned run/evidence pass `validate_agent_run` and `validate_research_evidence`.
- [ ] Assert no `startedAt`, `budget == {}`, `usage == {}`, `tasks == []`.
- [ ] Assert deterministic IDs and artifact/evidence refs derive from full selection SHA-256.

### Task 2: Enforce fail-closed owner handshake

**Files:**
- Modify: `apps/dashboard/tests/test_ai_stock_picker_adapter.py`
- Modify: `apps/dashboard/src/trading_research/ai_stock_picker_adapter.py`

- [ ] Add failing tests for selection SHA mismatch.
- [ ] Add failing tests for unsupported receipt schema/artifact type/profile.
- [ ] Add failing tests for `valid != true`, market mismatch, prompt mismatch, as-of mismatch and pick-count mismatch.
- [ ] Add failing tests for unsupported selection schema/artifact type/selection method.
- [ ] Add failing tests for malformed owner lineage hashes and malformed receipt evidence manifest hash.
- [ ] Implement only the checks required by those tests.

### Task 3: Preserve PIT/OOS and evidence strength

**Files:**
- Modify: `apps/dashboard/tests/test_ai_stock_picker_adapter.py`
- Modify: `apps/dashboard/src/trading_research/ai_stock_picker_adapter.py`

- [ ] Assert `signal_date_only/false/false` maps unchanged.
- [ ] Assert all producer `evidence_limitations` are preserved.
- [ ] Assert format-only response verification adds `provider_response_not_byte_exact_revalidated`.
- [ ] Assert byte-exact evidence does not add that limitation and preserves `evidenceManifestSha256` provenance.
- [ ] Assert `adapted_at` maps only to evidence `retrievedAt`.

### Task 4: Document and verify

**Files:**
- Create: `apps/dashboard/docs/ai-stock-picker-adapter.md`
- Update PR description.

- [ ] Document producer/consumer boundary, required receipt, mapping and limitations.
- [ ] Run Dashboard PR CI.
- [ ] Confirm Dashboard Python tests, Research Core tests/ruff and Web tests/build pass.
- [ ] Inspect changed-file scope and ensure no credentials, raw market data, provider response or external source copy is committed.
- [ ] Keep PR Draft while producer PR #109 remains unverified/unmerged.
