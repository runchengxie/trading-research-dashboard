# M1 Niu Men 历史导入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `niu-men-line-strategy` 在精确源提交 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` 的允许历史迁入 `packages/niu-men-line-strategy/`，保留可审计 Git 历史，同时继续排除研究产物、凭据、源仓库 CI 和其他受保护路径。

**Architecture:** 在独立迁移 worktree 中，从精确 Niu Men 源提交构造只含批准路径的临时 Git 历史，再统一改写到 `packages/niu-men-line-strategy/` 并以 unrelated-history merge 合入 monorepo。M1 只改变代码所有权与治理边界，不抽取 `research-core`、不建立 uv workspace、不修改策略逻辑，也不改变 `niu_men.research_snapshot.v2` wire contract。

**Tech Stack:** Git、`git-filter-repo`、Python 3.11、uv、pytest、coverage、Ruff、ty、pip-audit，以及根级 foundation checker / GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-08-26-m1-history-preserving-imports-design.md`

## Global Constraints

- 源仓库固定为 `runchengxie/niu-men-line-strategy`，源提交固定为 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb`。
- 目标前缀固定为 `packages/niu-men-line-strategy/`。
- 只允许导入设计中明确批准的 `src/`、`scripts/`、`tests/`、schema、根元数据和指定 docs。
- 不导入 `artifacts/`、生成 OOS CSV/JSON、研究结果文档、`docs/original-transcript.md`、`.github/`、`.env*`、credential/secret/token/password 文件和私钥材料。
- 源 `uv.lock` 不进入 M1 历史；M3 再统一 workspace 与锁文件策略。
- 保持 Python `>=3.11`、Niu Men 策略逻辑、执行时序、provenance/quality semantics 和 `niu_men.research_snapshot.v2` 不变。
- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 继续留在 monorepo 外。
- 不创建 submodule、gitlink、长期临时 remote，也不直接修改共享 `main` worktree。
- GitHub Actions 继续保持 manual-only，不重新启用 PR/push 自动触发。

---

### Task 1: 建立 Niu Men 导入清单与回滚记录

**Files:**
- Create: `docs/migration/niu-men-import.md`
- Modify: `docs/migration/README.md`
- Modify: `docs/migration/source-commits.md`

**Interfaces:**
- Consumes: approved M1 source/path boundary from the spec.
- Produces: reviewer-readable import manifest used by Tasks 2–5 as the canonical allowlist and audit record.

- [ ] **Step 1: 写入精确路径映射**

`docs/migration/niu-men-import.md` 必须记录：

```text
src/                                  -> packages/niu-men-line-strategy/src/
scripts/                              -> packages/niu-men-line-strategy/scripts/
tests/                                -> packages/niu-men-line-strategy/tests/
schemas/research-snapshot.schema.json -> packages/niu-men-line-strategy/schemas/research-snapshot.schema.json
README.md                             -> packages/niu-men-line-strategy/README.md
pyproject.toml                        -> packages/niu-men-line-strategy/pyproject.toml
.gitignore                            -> packages/niu-men-line-strategy/.gitignore
docs/README.md                        -> packages/niu-men-line-strategy/docs/README.md
docs/a1-integration.md                -> packages/niu-men-line-strategy/docs/a1-integration.md
docs/dashboard-snapshot.md            -> packages/niu-men-line-strategy/docs/dashboard-snapshot.md
docs/data-contract.md                 -> packages/niu-men-line-strategy/docs/data-contract.md
docs/maintenance-and-quality.md       -> packages/niu-men-line-strategy/docs/maintenance-and-quality.md
docs/oos-stability-diagnostics.md     -> packages/niu-men-line-strategy/docs/oos-stability-diagnostics.md
docs/restricted-strategy-notes.md            -> packages/niu-men-line-strategy/docs/restricted-strategy-notes.md
docs/portfolio-backtester-adapter.md  -> packages/niu-men-line-strategy/docs/portfolio-backtester-adapter.md
docs/strategy-spec.md                 -> packages/niu-men-line-strategy/docs/strategy-spec.md
```

同时明确说明排除规则作用于**重写后的完整历史**，不能只从最终 checkout 删除。

- [ ] **Step 2: 更新迁移状态**

把 `docs/migration/README.md` 的 M1 状态更新为 Dashboard 已完成、Niu Men 进行中；`source-commits.md` 保留源提交 `1be7f725...` 作为 rollback point，并链接 `niu-men-import.md`。

- [ ] **Step 3: 验证文档**

Run:

```bash
rg -n "1be7f725772fa824ce34e2bb833867cb4c3e9fcb|niu-men-line-strategy|original-transcript|artifacts|research_snapshot.v2" docs/migration
git diff --check
```

Expected: 所有导入边界和 rollback point 可检索，`git diff --check` exit 0。

- [ ] **Step 4: Commit**

```bash
git add docs/migration/niu-men-import.md docs/migration/README.md docs/migration/source-commits.md
git commit -m "docs: record Niu Men M1 import manifest"
```

### Task 2: 构造并合入 history-preserving Niu Men 历史

**Files:**
- Replace placeholder tree under: `packages/niu-men-line-strategy/`
- No changes outside the import prefix except the merge commit itself.

**Interfaces:**
- Consumes: exact allowlist from Task 1.
- Produces: filtered Git ancestry reachable through representative files under `packages/niu-men-line-strategy/`.

- [ ] **Step 1: 建立只锚定精确提交的临时源仓库**

```bash
IMPORT_TMP=$(mktemp -d)
SOURCE_TMP="$IMPORT_TMP/niu-men-source"
SOURCE_URL="https://github.com/runchengxie/niu-men-line-strategy.git"
SOURCE_SHA="1be7f725772fa824ce34e2bb833867cb4c3e9fcb"

git init -q "$SOURCE_TMP"
git -C "$SOURCE_TMP" remote add origin "$SOURCE_URL"
git -C "$SOURCE_TMP" fetch --no-tags origin "$SOURCE_SHA"
git -C "$SOURCE_TMP" checkout -b import-source FETCH_HEAD
cp "$SOURCE_TMP/uv.lock" "$IMPORT_TMP/source-uv.lock"
git -C "$SOURCE_TMP" remote remove origin
```

Expected: `git -C "$SOURCE_TMP" rev-parse HEAD` exactly equals `1be7f725...` and the source lock is retained only as a temporary validation aid.

- [ ] **Step 2: 只保留批准路径并重写前缀**

```bash
cd "$SOURCE_TMP"
uvx --from git-filter-repo git-filter-repo --force \
  --path src/ \
  --path scripts/ \
  --path tests/ \
  --path schemas/research-snapshot.schema.json \
  --path README.md \
  --path pyproject.toml \
  --path .gitignore \
  --path docs/README.md \
  --path docs/a1-integration.md \
  --path docs/dashboard-snapshot.md \
  --path docs/data-contract.md \
  --path docs/maintenance-and-quality.md \
  --path docs/oos-stability-diagnostics.md \
  --path docs/restricted-strategy-notes.md \
  --path docs/portfolio-backtester-adapter.md \
  --path docs/strategy-spec.md \
  --path-rename src/:packages/niu-men-line-strategy/src/ \
  --path-rename scripts/:packages/niu-men-line-strategy/scripts/ \
  --path-rename tests/:packages/niu-men-line-strategy/tests/ \
  --path-rename schemas/:packages/niu-men-line-strategy/schemas/ \
  --path-rename docs/:packages/niu-men-line-strategy/docs/ \
  --path-rename README.md:packages/niu-men-line-strategy/README.md \
  --path-rename pyproject.toml:packages/niu-men-line-strategy/pyproject.toml \
  --path-rename .gitignore:packages/niu-men-line-strategy/.gitignore
```

Expected: tree root contains only `packages/niu-men-line-strategy/`.

- [ ] **Step 3: 从重写历史剔除敏感名字**

```bash
uvx --from git-filter-repo git-filter-repo --force --invert-paths \
  --path-regex '^packages/niu-men-line-strategy/(.*/)?\.env[^/]*$' \
  --path-regex '^packages/niu-men-line-strategy/(.*/)?[^/]*(credential|secret|token|password)[^/]*$' \
  --path-regex '^packages/niu-men-line-strategy/(.*/)?[^/]*\.(pem|key|p12|pfx)$'
```

Expected: protected-name audit returns no path. The explicit allowlist already prevents `.github/`, `artifacts/`, `docs/original-transcript.md`, result docs and source `uv.lock` from entering history.

- [ ] **Step 4: 合入迁移 worktree**

From the dedicated monorepo worktree on `feat/m1-niu-men-history-import`:

```bash
git remote add niu-men-m1 "$SOURCE_TMP"
git fetch niu-men-m1 import-source
git merge --allow-unrelated-histories --no-commit FETCH_HEAD
```

Resolve only the expected placeholder conflict at `packages/niu-men-line-strategy/README.md`: keep the imported README content and append the monorepo ownership note. No strategy/source edits are allowed in this task.

Then:

```bash
git commit -m "feat: import Niu Men history into monorepo"
git remote remove niu-men-m1
```

- [ ] **Step 5: 验证历史边界**

```bash
git log --follow --oneline -- packages/niu-men-line-strategy/src/niu_men_line_strategy/signals.py | head -20
git log --all --name-only --format= | grep -E '^(packages/niu-men-line-strategy/(artifacts/|\.github/|docs/original-transcript\.md|uv\.lock)$|packages/niu-men-line-strategy/(.*/)?\.env[^/]*$|packages/niu-men-line-strategy/(.*/)?[^/]*(credential|secret|token|password)[^/]*$|packages/niu-men-line-strategy/(.*/)?[^/]*\.(pem|key|p12|pfx)$)' && exit 1 || true
git ls-files --stage | awk '$1 == "160000" {print}'
git submodule status
git diff --check
```

Expected: `git log --follow` reaches pre-monorepo Niu Men history; protected-history, gitlink and submodule outputs are empty; whitespace check passes.

### Task 3: 用 TDD 扩展 monorepo foundation 边界

**Files:**
- Modify: `tests/test_foundation.py`
- Modify: `scripts/check_foundation.py`
- Modify: `README.md`
- Modify: `docs/migration/README.md`
- Modify: `.github/workflows/foundation.yml`

**Interfaces:**
- Consumes: imported Niu Men path set from Task 2.
- Produces: deterministic allowlist that accepts only approved Niu Men paths and rejects protected paths.

- [ ] **Step 1: 先写失败边界测试**

Extend `test_tracked_file_respects_the_m1_boundary` with these cases:

```python
(
    "packages/niu-men-line-strategy/src/niu_men_line_strategy/signals.py",
    "def generate_signal():\n    return None\n",
    True,
),
(
    "packages/niu-men-line-strategy/scripts/publish_dashboard_snapshot.py",
    "def main():\n    return 0\n",
    True,
),
("packages/niu-men-line-strategy/docs/strategy-spec.md", "# spec\n", True),
("packages/niu-men-line-strategy/schemas/research-snapshot.schema.json", "{}\n", True),
("packages/niu-men-line-strategy/artifacts/result.json", "{}\n", False),
("packages/niu-men-line-strategy/.github/workflows/ci.yml", "name: ci\n", False),
("packages/niu-men-line-strategy/docs/original-transcript.md", "source\n", False),
("packages/niu-men-line-strategy/uv.lock", "version = 1\n", False),
("packages/niu-men-line-strategy/.env", "TOKEN=secret\n", False),
```

Run:

```bash
uv run --locked --extra dev pytest tests/test_foundation.py::test_tracked_file_respects_the_m1_boundary -q
```

Expected: FAIL because approved Niu Men paths are still rejected by the Dashboard-only boundary.

- [ ] **Step 2: 实现最小 allowlist**

Add exact Niu Men boundaries to `scripts/check_foundation.py`:

```python
NIU_MEN_ALLOWED_DIRECTORY_PREFIXES = (
    "packages/niu-men-line-strategy/src/",
    "packages/niu-men-line-strategy/scripts/",
    "packages/niu-men-line-strategy/tests/",
)

NIU_MEN_ALLOWED_FILES = frozenset(
    (
        "packages/niu-men-line-strategy/.gitignore",
        "packages/niu-men-line-strategy/README.md",
        "packages/niu-men-line-strategy/pyproject.toml",
        "packages/niu-men-line-strategy/schemas/research-snapshot.schema.json",
        "packages/niu-men-line-strategy/docs/README.md",
        "packages/niu-men-line-strategy/docs/a1-integration.md",
        "packages/niu-men-line-strategy/docs/dashboard-snapshot.md",
        "packages/niu-men-line-strategy/docs/data-contract.md",
        "packages/niu-men-line-strategy/docs/maintenance-and-quality.md",
        "packages/niu-men-line-strategy/docs/oos-stability-diagnostics.md",
        "packages/niu-men-line-strategy/docs/restricted-strategy-notes.md",
        "packages/niu-men-line-strategy/docs/portfolio-backtester-adapter.md",
        "packages/niu-men-line-strategy/docs/strategy-spec.md",
    )
)
```

Update `is_allowed_tracked_file()` so these exact files/prefixes are accepted after the existing forbidden-path check. Add `docs/migration/niu-men-import.md` to required/foundation files.

- [ ] **Step 3: 验证 RED → GREEN**

```bash
uv run --locked --extra dev pytest tests/test_foundation.py -q
uv run --locked python scripts/check_foundation.py
```

Expected: foundation tests pass and checker prints `Foundation check passed`.

- [ ] **Step 4: 更新根状态与 manual workflow**

Root README must state that both Dashboard and Niu Men M1 imports now live in the monorepo, while runtime authority and M2 extraction remain pending.

Append manual-only Niu Men validation steps to `.github/workflows/foundation.yml`; do not add PR/push triggers:

```yaml
      - name: Run Niu Men Python tests
        working-directory: packages/niu-men-line-strategy
        run: uv run --extra dev pytest

      - name: Run Niu Men lint and type checks
        working-directory: packages/niu-men-line-strategy
        run: |
          uv run --extra dev ruff check .
          uv run --extra dev ruff format --check .
          uv run --extra dev ty check src

      - name: Run Niu Men coverage gate
        working-directory: packages/niu-men-line-strategy
        run: |
          uv run --extra dev coverage run -m pytest
          uv run --extra dev coverage report --fail-under=80

      - name: Audit Niu Men Python dependencies
        working-directory: packages/niu-men-line-strategy
        run: uv run --extra dev pip-audit --skip-editable
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_foundation.py scripts/check_foundation.py README.md docs/migration/README.md .github/workflows/foundation.yml
git commit -m "build: integrate Niu Men M1 boundary checks"
```

### Task 4: 验证导入代码没有行为漂移

**Files:**
- No production-code modifications unless a path-only compatibility defect is reproduced by a failing test.
- Temporary only: `packages/niu-men-line-strategy/uv.lock` copied from `$IMPORT_TMP/source-uv.lock`, then removed before commit.

**Interfaces:**
- Consumes: imported source tree and source lock captured before filtering.
- Produces: source-package verification evidence without committing a nested M1 lockfile.

- [ ] **Step 1: 临时恢复源 lock 供验证**

```bash
cp "$IMPORT_TMP/source-uv.lock" packages/niu-men-line-strategy/uv.lock
uv lock --project packages/niu-men-line-strategy --check
```

Expected: source lock remains compatible with the imported unchanged `pyproject.toml`.

- [ ] **Step 2: 运行 Niu Men source-required gates**

```bash
cd packages/niu-men-line-strategy
uv run --locked --extra dev pytest
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev ty check src
uv run --locked --extra dev coverage run -m pytest
uv run --locked --extra dev coverage report --fail-under=80
uv run --locked --extra dev pip-audit --skip-editable
cd ../..
```

Expected: every command exits 0. If a path-rewrite compatibility defect appears, first add a deterministic regression test, prove it fails, then apply the smallest path-only fix. Do not change strategy calculations or contract semantics in M1.

- [ ] **Step 3: 删除临时 nested lock 并确认未跟踪**

```bash
rm packages/niu-men-line-strategy/uv.lock
test ! -e packages/niu-men-line-strategy/uv.lock
git status --short
```

Expected: no `uv.lock` under the Niu Men package and no unrelated generated artifacts.

- [ ] **Step 4: 运行完整 monorepo gates**

```bash
uv lock --check
uv lock --project apps/dashboard --check
uvx --from ruff==0.16.4 ruff check --select E4,E7,E9,F scripts tests apps/dashboard/scripts apps/dashboard/src apps/dashboard/tests
uv run --locked --extra dev pytest -q
uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests
uv run --project apps/dashboard --locked --all-extras --with pip-audit==2.10.1 pip-audit --progress-spinner off
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npm audit --prefix apps/dashboard/web --audit-level=high
uv run --locked python scripts/check_foundation.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 5: 写入精确验证审计**

Append to `docs/migration/niu-men-import.md`:
- exact Niu Men test/lint/type/coverage/audit outputs;
- root/Dashboard gate outputs;
- representative `git log --follow` evidence;
- empty protected-history/gitlink/submodule evidence;
- source commit and rollback point;
- confirmation that original source repository was not modified.

Commit:

```bash
git add docs/migration/niu-men-import.md
git commit -m "docs: record Niu Men M1 validation evidence"
```

### Task 5: 完成 Draft PR #9 并进入审查

**Files:**
- PR metadata only.

**Interfaces:**
- Consumes: Tasks 1–4 and their verification evidence.
- Produces: one independently reviewable Niu Men M1 PR; M2 must not start implementation until this PR is merged.

- [ ] **Step 1: 最终 diff 与边界审计**

```bash
git status --short
git diff --check main...HEAD
git log --oneline --decorate main..HEAD
```

Expected: branch contains only Niu Men M1 import, governance integration, migration docs, and this approved plan.

- [ ] **Step 2: Push**

```bash
git push -u origin feat/m1-niu-men-history-import
```

- [ ] **Step 3: 更新 Draft PR**

PR title:

```text
feat: import Niu Men history into monorepo
```

PR body must summarize:
- source commit `1be7f725...`;
- exact allowed/excluded history boundary;
- no strategy/wire-contract/workspace changes;
- exact verification evidence;
- rollback point;
- M2 `research-core` remains a separate follow-up PR.

- [ ] **Step 4: Ready gate**

Only mark Ready when history audit, Niu Men source gates, monorepo foundation, Dashboard gates, Python audits, frontend tests/build/audit, and whitespace checks all have fresh exit-0 evidence. Do not merge from this task without separate review.
