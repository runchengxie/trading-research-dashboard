# M2 Research Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved M2 `research-core` package so `niu_men.research_snapshot.v2` has one canonical schema/fixture owner and shared Python structural/provenance validation without changing the wire protocol.

**Architecture:** `packages/research-core` becomes a small installable package. Its schema is package data loaded with `importlib.resources`; its four fixtures are canonical test assets. Root, Dashboard and Niu Men keep temporary compatibility mirrors guarded by synchronization tests. M3, not M2, introduces the uv workspace and production package dependencies.

**Tech Stack:** Python 3.11+, hatchling, jsonschema Draft 2020-12, pytest, Ruff, uv, existing Dashboard TypeScript/Vite tests.

**Spec:** `docs/superpowers/specs/2026-08-26-m2-research-core-design.md`

## Global Constraints

- Production implementation is blocked until issue #13 is complete and the real Niu Men history/source import exists on `main`.
- Keep wire version exactly `niu_men.research_snapshot.v2`.
- `research-core` owns contract validation only; no Niu Men strategy logic, Dashboard UI logic, market-data fetching or research execution enters this package.
- Python requirement is `>=3.11`.
- Runtime dependency is limited to `jsonschema>=4.23,<5`.
- Do not create `packages/research-core/uv.lock` in M2.
- Do not convert the root project to a uv workspace in M2.
- Dashboard TypeScript `parseResearchSnapshot()` remains the browser consumer parser.
- Root/Dashboard/Niu Men schema and fixture copies remain compatibility mirrors until M3 decides which can be removed.
- Raw market data, full OOS outputs, credentials and local data roots remain outside Git.

---

### Task 0: Verify the M1 corrective import gate

**Files:**
- Read: `packages/niu-men-line-strategy/src/**`
- Read: `packages/niu-men-line-strategy/tests/**`
- Read: `packages/niu-men-line-strategy/scripts/**`
- Read: `packages/niu-men-line-strategy/schemas/research-snapshot.schema.json`
- Read: `packages/niu-men-line-strategy/pyproject.toml`
- Read: `docs/migration/niu-men-import.md`

**Interfaces:**
- Consumes: issue #13 completion evidence.
- Produces: a verified implementation baseline for all later tasks.

- [ ] **Step 1: Verify required paths exist**

```bash
test -d packages/niu-men-line-strategy/src
test -d packages/niu-men-line-strategy/tests
test -d packages/niu-men-line-strategy/scripts
test -f packages/niu-men-line-strategy/schemas/research-snapshot.schema.json
test -f packages/niu-men-line-strategy/pyproject.toml
```

Expected: all commands exit 0. If any fail, stop M2 and finish #13 first.

- [ ] **Step 2: Verify representative source history**

```bash
git log --follow --oneline -- \
  packages/niu-men-line-strategy/src/niu_men_line_strategy/signals.py | head -20
```

Expected: source history extends beyond a single monorepo copy commit and reaches the imported Niu Men history.

- [ ] **Step 3: Re-run the corrective M1 validation gates**

Run the exact Niu Men pytest, Ruff, format, ty, coverage, pip-audit and monorepo foundation commands recorded by the corrective import PR.

Expected: all gates pass before Task 1 begins.

### Task 1: Create the package metadata and RED tests

**Files:**
- Modify: `packages/research-core/README.md`
- Create: `packages/research-core/pyproject.toml`
- Create: `packages/research-core/src/research_core/__init__.py`
- Create: `packages/research-core/src/research_core/schemas/__init__.py`
- Create: `packages/research-core/tests/test_snapshot.py`
- Create: `packages/research-core/tests/test_provenance.py`

**Interfaces:**
- Consumes: Python 3.11 and `jsonschema>=4.23,<5`.
- Produces: package namespace `research_core` and failing behavioural tests.

- [ ] **Step 1: Add package metadata**

Create `packages/research-core/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[project]
name = "research-core"
version = "0.1.0"
description = "Shared research snapshot contracts for the A-share trading research monorepo"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["jsonschema>=4.23,<5"]

[tool.hatch.build.targets.wheel]
packages = ["src/research_core"]

[tool.hatch.build.targets.sdist]
include = ["README.md", "src/research_core/**", "tests/**"]

[dependency-groups]
dev = ["pytest>=8.3,<9", "ruff>=0.9"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Add a minimal package namespace**

Create `src/research_core/__init__.py`:

```python
"""Shared research contracts."""

__all__: list[str] = []
```

Create `src/research_core/schemas/__init__.py`:

```python
"""Packaged JSON Schemas for research-core."""
```

This namespace deliberately does not import `snapshot` or `provenance` yet. Doing so before those modules exist would make later focused tests fail during package import rather than for the intended missing behaviour.

- [ ] **Step 3: Write failing snapshot tests**

Create `tests/test_snapshot.py`:

```python
import json
from pathlib import Path

import pytest

from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "research_snapshot"


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_schema_version_is_v2() -> None:
    assert SCHEMA_VERSION == "niu_men.research_snapshot.v2"


def test_valid_v2_passes() -> None:
    validate_snapshot(read_fixture("valid_v2.json"))


def test_warning_v2_is_structurally_valid() -> None:
    validate_snapshot(read_fixture("warning_v2.json"))


def test_missing_required_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_snapshot(read_fixture("invalid_missing_required.json"))


def test_unsupported_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="schemaVersion"):
        validate_snapshot(read_fixture("unsupported_version.json"))


def test_non_mapping_root_is_rejected() -> None:
    with pytest.raises(TypeError, match="root must be an object"):
        validate_snapshot([])  # type: ignore[arg-type]


def test_load_snapshot_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_snapshot(path)
```

- [ ] **Step 4: Write failing provenance tests**

Create `tests/test_provenance.py`:

```python
import copy
import json
from pathlib import Path

import pytest

from research_core.provenance import (
    missing_provenance_fields,
    provenance_complete,
    validate_provenance_consistency,
)

FIXTURES = Path(__file__).parent / "fixtures" / "research_snapshot"


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_v2_has_complete_provenance() -> None:
    snapshot = read_fixture("valid_v2.json")
    assert missing_provenance_fields(snapshot) == ()
    assert provenance_complete(snapshot) is True
    validate_provenance_consistency(snapshot)


def test_warning_v2_reports_missing_provenance() -> None:
    snapshot = read_fixture("warning_v2.json")
    assert missing_provenance_fields(snapshot) == (
        "source.researchCommit",
        "source.dataPlatformManifest.schemaVersion",
        "source.dataPlatformManifest.generatedAt",
    )
    assert provenance_complete(snapshot) is False
    validate_provenance_consistency(snapshot)


def test_declared_complete_must_match_actual_fields() -> None:
    snapshot = read_fixture("warning_v2.json")
    snapshot["quality"]["checks"]["provenanceComplete"] = True
    with pytest.raises(ValueError, match="provenanceComplete"):
        validate_provenance_consistency(snapshot)


def test_incomplete_provenance_requires_warning_status() -> None:
    snapshot = read_fixture("warning_v2.json")
    snapshot["quality"]["status"] = "pass"
    with pytest.raises(ValueError, match="quality.status"):
        validate_provenance_consistency(snapshot)


def test_empty_string_counts_as_missing() -> None:
    snapshot = copy.deepcopy(read_fixture("valid_v2.json"))
    snapshot["source"]["researchCommit"] = ""
    assert provenance_complete(snapshot) is False
```

- [ ] **Step 5: Verify RED**

```bash
uv run --project packages/research-core --group dev pytest -q
```

Expected: collection fails because `research_core.snapshot` and `research_core.provenance` do not exist.

- [ ] **Step 6: Commit**

```bash
git add packages/research-core
git commit -m "test: define research-core contract behavior"
```

### Task 2: Add canonical assets and structural validation

**Files:**
- Create: `packages/research-core/src/research_core/schemas/research-snapshot.schema.json`
- Create: `packages/research-core/tests/fixtures/research_snapshot/*.json`
- Create: `packages/research-core/src/research_core/snapshot.py`
- Modify: `packages/research-core/src/research_core/__init__.py`

**Interfaces:**
- Produces: `SCHEMA_VERSION`, `validate_snapshot()`, `load_snapshot()`.

- [ ] **Step 1: Cross-check Niu Men and Dashboard copies before choosing canonical assets**

```bash
python - <<'PY'
import json
from pathlib import Path

left = Path("packages/niu-men-line-strategy/schemas/research-snapshot.schema.json")
right = Path("apps/dashboard/schemas/research-snapshot.schema.json")
assert json.loads(left.read_text()) == json.loads(right.read_text())

for name in (
    "valid_v2.json",
    "warning_v2.json",
    "invalid_missing_required.json",
    "unsupported_version.json",
):
    left = Path("packages/niu-men-line-strategy/tests/fixtures/research_snapshot") / name
    right = Path("apps/dashboard/tests/fixtures/research_snapshot") / name
    assert json.loads(left.read_text()) == json.loads(right.read_text()), name
PY
```

Expected: exit 0. Any mismatch is investigated before canonicalization.

- [ ] **Step 2: Copy the verified canonical schema and fixtures**

```bash
mkdir -p packages/research-core/src/research_core/schemas
mkdir -p packages/research-core/tests/fixtures/research_snapshot
cp packages/niu-men-line-strategy/schemas/research-snapshot.schema.json \
  packages/research-core/src/research_core/schemas/research-snapshot.schema.json
cp packages/niu-men-line-strategy/tests/fixtures/research_snapshot/*.json \
  packages/research-core/tests/fixtures/research_snapshot/
```

- [ ] **Step 3: Implement `snapshot.py`**

```python
from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "niu_men.research_snapshot.v2"
_SCHEMA_RESOURCE = files("research_core.schemas").joinpath("research-snapshot.schema.json")
_SCHEMA = json.loads(_SCHEMA_RESOURCE.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _error_location(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "root"


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot schema validation failed: root must be an object")
    errors = sorted(
        _VALIDATOR.iter_errors(snapshot),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ValueError(
            f"snapshot schema validation failed at {_error_location(error)}: {error.message}"
        )


def load_snapshot(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"snapshot schema validation failed: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TypeError("snapshot schema validation failed: root must be an object")
    validate_snapshot(payload)
    return payload
```

- [ ] **Step 4: Export snapshot API only**

Replace `research_core/__init__.py` with:

```python
"""Shared research contracts."""

from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot

__all__ = ["SCHEMA_VERSION", "load_snapshot", "validate_snapshot"]
```

- [ ] **Step 5: Verify snapshot GREEN**

```bash
uv run --project packages/research-core --group dev pytest -q tests/test_snapshot.py
```

Expected: snapshot tests pass. Provenance tests remain red because Task 3 has not created `provenance.py`.

- [ ] **Step 6: Commit**

```bash
git add packages/research-core
git commit -m "feat: add canonical research snapshot validation"
```

### Task 3: Implement provenance semantics and complete package exports

**Files:**
- Create: `packages/research-core/src/research_core/provenance.py`
- Modify: `packages/research-core/src/research_core/__init__.py`
- Test: `packages/research-core/tests/test_provenance.py`

**Interfaces:**
- Produces: `PROVENANCE_FIELDS`, `missing_provenance_fields()`, `provenance_complete()`, `validate_provenance_consistency()`.

- [ ] **Step 1: Implement provenance logic**

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PROVENANCE_FIELDS = (
    "source.researchCommit",
    "source.dataPlatformManifest.schemaVersion",
    "source.dataPlatformManifest.generatedAt",
)
_MISSING = object()


def _lookup(snapshot: Mapping[str, Any], dotted_path: str) -> Any:
    value: Any = snapshot
    for part in dotted_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _is_missing(value: Any) -> bool:
    return value is _MISSING or value is None or (
        isinstance(value, str) and not value.strip()
    )


def missing_provenance_fields(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        path for path in PROVENANCE_FIELDS if _is_missing(_lookup(snapshot, path))
    )


def provenance_complete(snapshot: Mapping[str, Any]) -> bool:
    return not missing_provenance_fields(snapshot)


def validate_provenance_consistency(snapshot: Mapping[str, Any]) -> None:
    actual = provenance_complete(snapshot)
    declared = _lookup(snapshot, "quality.checks.provenanceComplete")
    if not isinstance(declared, bool):
        raise ValueError("quality.checks.provenanceComplete must be a boolean")
    if declared != actual:
        raise ValueError(
            "quality.checks.provenanceComplete does not match actual provenance completeness"
        )
    if not actual and _lookup(snapshot, "quality.status") != "warning":
        raise ValueError("quality.status must be warning when provenance is incomplete")
```

- [ ] **Step 2: Export provenance API**

Update `research_core/__init__.py`:

```python
from research_core.provenance import (
    PROVENANCE_FIELDS,
    missing_provenance_fields,
    provenance_complete,
    validate_provenance_consistency,
)
from research_core.snapshot import SCHEMA_VERSION, load_snapshot, validate_snapshot

__all__ = [
    "PROVENANCE_FIELDS",
    "SCHEMA_VERSION",
    "load_snapshot",
    "missing_provenance_fields",
    "provenance_complete",
    "validate_provenance_consistency",
    "validate_snapshot",
]
```

- [ ] **Step 3: Verify complete package GREEN**

```bash
uv run --project packages/research-core --group dev pytest -q
uv run --project packages/research-core --group dev ruff check src tests
```

Expected: all package tests and Ruff pass.

- [ ] **Step 4: Verify installed-package resource loading**

```bash
TMP_VENV=$(mktemp -d)
uv venv "$TMP_VENV/venv"
uv pip install --python "$TMP_VENV/venv/bin/python" ./packages/research-core
"$TMP_VENV/venv/bin/python" - <<'PY'
from research_core.snapshot import SCHEMA_VERSION
assert SCHEMA_VERSION == "niu_men.research_snapshot.v2"
PY
rm -rf "$TMP_VENV"
```

Expected: import succeeds outside source-tree path assumptions.

- [ ] **Step 5: Commit**

```bash
git add packages/research-core
git commit -m "feat: validate research snapshot provenance"
```

### Task 4: Add compatibility mirrors and drift tests

**Files:**
- Create/Modify: `schemas/research-snapshot.schema.json`
- Modify: Dashboard and Niu Men schema mirrors only through canonical synchronization
- Create: `tests/test_research_contract_sync.py`

**Interfaces:**
- Produces: deterministic proof that compatibility copies match canonical JSON semantics.

- [ ] **Step 1: Write the drift test first**

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SCHEMA = ROOT / "packages/research-core/src/research_core/schemas/research-snapshot.schema.json"
CANONICAL_FIXTURES = ROOT / "packages/research-core/tests/fixtures/research_snapshot"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_mirrors_match_canonical() -> None:
    expected = read_json(CANONICAL_SCHEMA)
    mirrors = (
        ROOT / "schemas/research-snapshot.schema.json",
        ROOT / "apps/dashboard/schemas/research-snapshot.schema.json",
        ROOT / "packages/niu-men-line-strategy/schemas/research-snapshot.schema.json",
    )
    for mirror in mirrors:
        assert read_json(mirror) == expected, mirror


def test_fixture_mirrors_match_canonical() -> None:
    for name in (
        "valid_v2.json",
        "warning_v2.json",
        "invalid_missing_required.json",
        "unsupported_version.json",
    ):
        expected = read_json(CANONICAL_FIXTURES / name)
        mirrors = (
            ROOT / "apps/dashboard/tests/fixtures/research_snapshot" / name,
            ROOT / "packages/niu-men-line-strategy/tests/fixtures/research_snapshot" / name,
        )
        for mirror in mirrors:
            assert read_json(mirror) == expected, mirror
```

- [ ] **Step 2: Verify RED before creating a missing root mirror**

```bash
uv run --locked --extra dev pytest -q tests/test_research_contract_sync.py
```

Expected: failure names the missing root schema mirror when it is absent.

- [ ] **Step 3: Synchronize schema mirrors from canonical**

```bash
mkdir -p schemas
cp packages/research-core/src/research_core/schemas/research-snapshot.schema.json \
  schemas/research-snapshot.schema.json
cp packages/research-core/src/research_core/schemas/research-snapshot.schema.json \
  apps/dashboard/schemas/research-snapshot.schema.json
cp packages/research-core/src/research_core/schemas/research-snapshot.schema.json \
  packages/niu-men-line-strategy/schemas/research-snapshot.schema.json
```

Only change fixture mirrors if the Task 2 cross-check found and explained a mismatch.

- [ ] **Step 4: Verify sync and Dashboard consumer regression**

```bash
uv run --locked --extra dev pytest -q tests/test_research_contract_sync.py
uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests
npm test --prefix apps/dashboard/web
```

Expected: all green and v1/v2 browser compatibility unchanged.

- [ ] **Step 5: Commit**

```bash
git add schemas tests/test_research_contract_sync.py \
  apps/dashboard/schemas packages/niu-men-line-strategy/schemas
git commit -m "test: keep research contract mirrors synchronized"
```

### Task 5: Integrate research-core into repository governance

**Files:**
- Modify: `scripts/check_foundation.py`
- Modify: `tests/test_foundation.py`
- Modify: `packages/research-core/README.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/roadmap/README.md`

**Interfaces:**
- Produces: explicit foundation ownership for the new package.

- [ ] **Step 1: Add failing foundation cases**

Positive paths:

```text
packages/research-core/pyproject.toml
packages/research-core/src/research_core/__init__.py
packages/research-core/src/research_core/snapshot.py
packages/research-core/src/research_core/provenance.py
packages/research-core/src/research_core/schemas/research-snapshot.schema.json
packages/research-core/tests/test_snapshot.py
packages/research-core/tests/test_provenance.py
packages/research-core/tests/fixtures/research_snapshot/valid_v2.json
schemas/research-snapshot.schema.json
```

Negative paths:

```text
packages/research-core/artifacts/results.json
packages/research-core/data/raw/example.csv
packages/research-core/.env
packages/research-core/research-output.csv
```

- [ ] **Step 2: Update checker with focused package prefixes/files**

Add explicit research-core package/test prefixes. Keep global raw-data/artifact/credential rejection ahead of allowlist evaluation.

- [ ] **Step 3: Update factual docs**

Mark M2 canonical ownership implemented while keeping M3 workspace status pending. Do not claim Niu Men production imports use `research_core` before #15 implements that dependency.

- [ ] **Step 4: Run focused governance tests**

```bash
uv run --locked --extra dev pytest -q \
  tests/test_foundation.py tests/test_research_contract_sync.py
uv run --locked python scripts/check_foundation.py
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_foundation.py tests/test_foundation.py \
  packages/research-core/README.md docs/migration/README.md docs/roadmap/README.md
git commit -m "build: integrate research-core governance"
```

### Task 6: Run full verification and prepare the implementation PR

**Files:**
- Verify all changed files.
- Update PR body with observed results only.

**Interfaces:**
- Produces: reviewable implementation PR for issue #14.

- [ ] **Step 1: Run Python gates**

```bash
uv run --project packages/research-core --group dev pytest -q
uv run --project packages/research-core --group dev ruff check src tests
uv run --locked --extra dev pytest -q
uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests
uv run --project packages/niu-men-line-strategy --group dev pytest -q
uv run --locked python scripts/check_foundation.py
```

Also run the imported Niu Men `AGENTS.md` Ruff/format/ty/coverage commands exactly.

- [ ] **Step 2: Run dependency audits**

```bash
uv run --project packages/research-core --group dev \
  --with pip-audit==2.10.1 pip-audit --progress-spinner off
uv run --project apps/dashboard --locked --all-extras \
  --with pip-audit==2.10.1 pip-audit --progress-spinner off
```

Run Niu Men pip-audit according to its imported repository rules.

- [ ] **Step 3: Run Dashboard Web regression**

```bash
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npm audit --prefix apps/dashboard/web --audit-level=high
```

- [ ] **Step 4: Enforce M2 lock boundary and whitespace**

```bash
test ! -f packages/research-core/uv.lock
uv lock --check
uv lock --project apps/dashboard --check
git diff --check
```

Use the Niu Men lock policy established by the corrective M1 PR; do not invent an extra M2 lockfile.

- [ ] **Step 5: Review scope**

Expected production changes are limited to `packages/research-core`, canonical/mirror schema assets, contract/foundation tests/checker and factual docs. Niu Men strategy implementations and Dashboard rendering logic remain unchanged.

- [ ] **Step 6: Open the M2 implementation PR**

Title:

```text
feat: implement research-core shared contracts
```

Body requirements:

- link #14 and #13;
- link the approved M2 design spec;
- list exact observed tests/audit results;
- state that workspace convergence is deferred to #15;
- keep Draft until all Task 6 gates have fresh evidence.

## Completion Gate

M2 is complete only when #13 is genuinely complete, all Task 6 gates have fresh passing evidence, and the implementation PR has been reviewed and merged. A merged plan or design PR does not satisfy this gate.
