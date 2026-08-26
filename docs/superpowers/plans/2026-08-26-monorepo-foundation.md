# A-Share Trading Research Monorepo Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reviewable M0 foundation for the private `a-share-trading-research` monorepo without importing or changing Dashboard or Niu Men implementation code.

**Architecture:** Establish root governance, a documented target layout, a small standard-library foundation checker, and CI that validates the boundary. Record the exact source commits for the two existing repositories so the later history-preserving import has a reproducible starting point. Keep `research-workspace` and market-data infrastructure outside the repository.

**Tech Stack:** Python 3.11+, uv, pytest, GitHub Actions, Markdown, standard-library path and text validation.

**Spec:** `docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md`

## Global Constraints

- This phase must not copy source implementation from either existing repository.
- The existing repositories remain active and independently usable.
- The repository is private because both source repositories are private.
- `research-workspace`, `market-data-platform`, and `etf-minute-fetcher` remain external projects.
- No git submodules are introduced.
- The monorepo must not become the runtime source of truth during M0.
- The wire version remains `niu_men.research_snapshot.v2`.
- Raw market data, full OOS CSV files, credentials, and local data roots are not committed.
- The root Python policy is `requires-python = ">=3.11"`; this does not migrate or alter the Python floors of the source repositories.
- Every implementation task starts with a failing test or structural check, except documentation and CI files that are immediately exercised by the checker.

---

### Task 1: Add the foundation boundary checker

**Files:**
- Create: `scripts/check_foundation.py`
- Create: `tests/test_foundation.py`

**Interfaces:**
- Consumes: a repository root `pathlib.Path`.
- Produces: `validate_foundation(root: Path) -> list[str]` and a CLI exit status through `main() -> int`.
- Later tasks rely on the checker to validate required directories, required foundation files, and forbidden boundary directories.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_foundation.py`:

~~~python
from pathlib import Path

from scripts.check_foundation import validate_foundation


def test_current_repository_has_a_complete_foundation() -> None:
    root = Path(__file__).resolve().parents[1]

    assert validate_foundation(root) == []


def test_missing_required_file_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")

    errors = validate_foundation(tmp_path)

    assert any("AGENTS.md" in error for error in errors)


def test_forbidden_external_project_directory_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# guidance\n", encoding="utf-8")
    (tmp_path / "research-workspace").mkdir()

    errors = validate_foundation(tmp_path)

    assert any("research-workspace" in error for error in errors)


def test_placeholder_markers_in_documentation_are_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# guidance\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.md").write_text("TODO: fill this\n", encoding="utf-8")

    errors = validate_foundation(tmp_path)

    assert any("placeholder" in error.lower() for error in errors)
~~~

- [ ] **Step 2: Run the tests to verify they fail**

Run:

~~~bash
uvx --with pytest pytest tests/test_foundation.py -q
~~~

Expected: FAIL with an import error because `scripts/check_foundation.py` does not yet exist.

- [ ] **Step 3: Implement the minimal checker**

Create `scripts/check_foundation.py`:

~~~python
"""Validate the M0 monorepo boundary and foundation files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_DIRECTORIES = (
    "apps/dashboard",
    "packages/research-core",
    "packages/niu-men-line-strategy",
    "docs/migration",
    "docs/superpowers/specs",
    "docs/superpowers/plans",
    "scripts",
    "tests",
)

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "pyproject.toml",
    "docs/migration/source-commits.md",
    "apps/dashboard/README.md",
    "packages/research-core/README.md",
    "packages/niu-men-line-strategy/README.md",
    "docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md",
    "docs/superpowers/plans/2026-08-26-monorepo-foundation.md",
    ".github/workflows/foundation.yml",
)

FORBIDDEN_DIRECTORIES = (
    "research-workspace",
    "market-data-platform",
    "etf-minute-fetcher",
)

PLACEHOLDER_PATTERN = re.compile(r"\b(?:TBD|TODO|FIXME)\b")


def validate_foundation(root: Path) -> list[str]:
    """Return deterministic validation errors for the M0 repository shape."""
    errors: list[str] = []
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"required directory missing: {relative}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"required file missing: {relative}")
    for relative in FORBIDDEN_DIRECTORIES:
        if (root / relative).exists():
            errors.append(f"forbidden external project directory present: {relative}")

    for markdown in sorted(root.rglob("*.md")):
        if ".git" in markdown.parts or "superpowers" in markdown.parts:
            continue
        text = markdown.read_text(encoding="utf-8")
        if PLACEHOLDER_PATTERN.search(text):
            errors.append(
                "placeholder marker found in documentation: "
                f"{markdown.relative_to(root)}"
            )
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_foundation(root)
    if errors:
        print("Foundation check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Foundation check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

- [ ] **Step 4: Run the focused tests again**

Run:

~~~bash
uvx --with pytest pytest tests/test_foundation.py -q
~~~

Expected: the temporary-root tests pass, while the repository completeness test remains red until Task 2 creates the required foundation files.

- [ ] **Step 5: Commit the checker**

~~~bash
git add scripts/check_foundation.py tests/test_foundation.py
git commit -m "test: define monorepo foundation boundary checks"
~~~

### Task 2: Add root governance and target-layout documentation

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `.gitignore`
- Create: `apps/dashboard/README.md`
- Create: `packages/research-core/README.md`
- Create: `packages/niu-men-line-strategy/README.md`
- Create: `docs/migration/README.md`
- Create: `docs/migration/source-commits.md`
- Create: `pyproject.toml`
- Create: `.github/workflows/foundation.yml`

**Interfaces:**
- Consumes: the boundary and migration rules in the approved design spec.
- Produces: documented directory markers that make the target ownership model explicit and allow the foundation checker to pass.

- [ ] **Step 1: Add the root README and contributor guidance**

`README.md` must state that this is the integration monorepo, list the current M0 status, show the target tree, and state that the two source repositories remain independently active.

`AGENTS.md` must contain:

~~~markdown
# Agent and contributor guidance

- Keep `research-workspace` and market-data infrastructure outside this repository.
- Do not commit raw market data, full OOS CSV files, credentials, or local data roots.
- Preserve `niu_men.research_snapshot.v2` during migration.
- Keep Dashboard and Niu Men boundaries separate until a migration PR explicitly changes them.
- Use a worktree and a pull request for each migration phase.
~~~

- [ ] **Step 2: Add boundary marker READMEs**

Create the three marker files with these exact responsibilities:

~~~markdown
# Dashboard application

Target location for the Dashboard application. Source import is deferred until the history-preserving import phase.
~~~

~~~markdown
# Research core

Target location for shared snapshot schema, fixtures, provenance rules, and small language-neutral validation helpers. Strategy logic does not belong here.
~~~

~~~markdown
# Niu Men strategy package

Target location for the Niu Men producer after history-preserving import. It remains a strategy package and does not own Dashboard presentation code.
~~~

- [ ] **Step 3: Add migration documentation with exact source commits**

`docs/migration/README.md` must summarize M0 through M4 and link to the design spec and this implementation plan.

`docs/migration/source-commits.md` must record:

~~~markdown
| Source | Repository | Import source commit | Current role |
| --- | --- | --- | --- |
| Dashboard | https://github.com/runchengxie/wu-t0-trading-dashboard | 8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114 | standalone Dashboard application |
| Niu Men | https://github.com/runchengxie/niu-men-line-strategy | 1be7f725772fa824ce34e2bb833867cb4c3e9fcb | standalone research and snapshot producer |
~~~

The file must also state that these commits are rollback points for the first import PR and that `research-workspace`, `market-data-platform`, and `etf-minute-fetcher` are intentionally excluded.

- [ ] **Step 4: Add safe repository ignore rules**

`.gitignore` must include:

~~~gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
node_modules/
dist/
playwright-report/
test-results/
.env
.env.*
data/
artifacts/raw/
artifacts/oos/
~~~

- [ ] **Step 5: Add root metadata and the foundation workflow**

Create `pyproject.toml`:

~~~toml
[project]
name = "a-share-trading-research"
version = "0.0.0"
description = "A-share trading research platform integration monorepo"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0,<9"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
~~~

Create `.github/workflows/foundation.yml`:

~~~yaml
name: Monorepo foundation

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  foundation:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: latest
          python-version: "3.11"

      - name: Run foundation tests
        run: uv run --extra dev pytest -q

      - name: Run foundation boundary check
        run: uv run python scripts/check_foundation.py

      - name: Check patch whitespace
        run: git diff --check
~~~

- [ ] **Step 6: Run the structural checks**

Run:

~~~bash
uv run --extra dev pytest tests/test_foundation.py -q
uv run python scripts/check_foundation.py
~~~

Expected: all foundation tests pass and the checker prints `Foundation check passed`.

- [ ] **Step 7: Commit the documentation, layout, and root metadata**

~~~bash
git add README.md AGENTS.md .gitignore apps packages docs/migration pyproject.toml .github/workflows/foundation.yml
git commit -m "docs: add monorepo foundation boundaries"
~~~

### Task 3: Generate the lockfile and verify the foundation

**Files:**
- Create: `uv.lock`

**Interfaces:**
- Consumes: `scripts/check_foundation.py` and `tests/test_foundation.py`.
- Produces: a root Python policy and a GitHub Actions check that validates the M0 repository shape on every pull request.

- [ ] **Step 1: Generate the lockfile and run the tests**

Run:

~~~bash
uv lock
uv run --extra dev pytest tests/test_foundation.py -q
~~~

Expected: the lockfile is generated and the foundation tests pass.

- [ ] **Step 2: Verify complete foundation locally**

Run:

~~~bash
uv run --extra dev pytest -q
uv run python scripts/check_foundation.py
git diff --check
~~~

Expected: all commands exit with status 0.

- [ ] **Step 3: Commit the lockfile**

~~~bash
git add uv.lock
git commit -m "build: lock monorepo foundation dependencies"
~~~

### Task 4: Review the M0 foundation and update PR #1

**Files:**
- Modify: none unless verification finds a concrete documentation or checker defect.

**Interfaces:**
- Consumes: all M0 files from Tasks 1–3.
- Produces: a reviewable PR that satisfies the design spec’s initial success criteria and contains no imported source implementation.

- [ ] **Step 1: Verify the repository contains only foundation files**

Run:

~~~bash
git status --short
git ls-files | sort
~~~

Confirm the tracked files are limited to governance, documentation, the checker/tests, root metadata/lock, and CI. There must be no Dashboard or Niu Men implementation files, raw OOS outputs, data directories, or credentials.

- [ ] **Step 2: Run final verification**

Run:

~~~bash
uv run --extra dev pytest -q
uv run python scripts/check_foundation.py
git diff --check
~~~

Expected: all commands exit with status 0.

- [ ] **Step 3: Push the completed M0 branch**

~~~bash
git push origin feat/monorepo-foundation
~~~

- [ ] **Step 4: Update PR #1**

The PR description must state that M0 creates only the foundation and that source imports are intentionally deferred. Include the exact verification commands and results. Do not merge the PR until the foundation layout and source-boundary review is complete.

## Deferred work after M0

The next plans must be separate and independently reviewable:

1. M1 history-preserving Dashboard import into `apps/dashboard/`.
2. M1 history-preserving Niu Men import into `packages/niu-men-line-strategy/`.
3. M2 extraction of `research-core` contract/provenance assets.
4. M3 Dashboard Python package migration and Python 3.11 convergence.
5. M4 path-aware CI, artifact handoff, and release cutover.

None of these tasks should be folded into the M0 foundation PR.
