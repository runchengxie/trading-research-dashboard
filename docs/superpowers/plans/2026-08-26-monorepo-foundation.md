# A 股交易研究 monorepo 基础实施计划

> Agent 执行提示：本计划记录 M0 基础阶段当时的任务拆分。M0 已经完成，后续维护不要把这里的旧 workflow 配置当成当前 CI 事实。

目标：建立私有 `trading-research-dashboard` monorepo 的可审查 M0 基础，不导入或修改 Dashboard、Niu Men 业务实现。

架构：先建立根级治理规则、目标目录、标准库实现的 foundation checker 和最小 CI，再记录两个源仓库的精确 commit，为后续保留历史导入提供可复现起点。`research-workspace` 和行情基础设施继续留在仓库外。

技术栈：Python 3.11+、uv、pytest、GitHub Actions、Markdown、标准库路径和文本校验。

设计依据：`docs/superpowers/specs/2026-08-26-trading-research-dashboard-monorepo-design.md`

## 全局约束

- M0 不复制两个源仓库的实现代码。
- 源仓库继续独立可用。
- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 保持外部项目身份。
- 不引入 Git submodule。
- M0 不宣称整个 monorepo 已经成为所有组件的运行来源。
- `niu_men.research_snapshot.v2` 保持不变。
- 不提交原始行情、完整 OOS CSV、凭据和本机数据目录。
- 根 Python 策略为 `requires-python = ">=3.11"`，不借 M0 修改源仓库版本要求。
- 除纯文档和 CI 文件外，实现任务先通过失败测试或结构检查定义预期。

---

### Task 1：建立 foundation boundary checker

新建：

```text
scripts/check_foundation.py
tests/test_foundation.py
```

目标接口：

```python
validate_foundation(root: Path) -> list[str]
main() -> int
```

- [ ] Step 1：先写失败测试

测试需要覆盖：

- 当前仓库基础完整性
- 缺少关键文件
- `research-workspace` 等外部目录误入仓库
- 普通 Markdown 中出现未完成占位词

- [ ] Step 2：确认测试因为 checker 尚不存在而失败

```bash
uvx --with pytest pytest tests/test_foundation.py -q
```

- [ ] Step 3：实现最小 checker

M0 版本负责检查：

- 必需目录
- 必需根文件
- 禁止的外部项目目录
- 普通 Markdown 中的 `TBD`、`TODO`、`FIXME`

`docs/superpowers/` 中的计划本身可以包含任务占位语义，不参与普通文档占位检查。

- [ ] Step 4：重新运行目标测试

```bash
uvx --with pytest pytest tests/test_foundation.py -q
```

临时目录测试应通过，当前仓库完整性测试等 Task 2 创建结构后再转绿。

- [ ] Step 5：提交 checker

```bash
git add scripts/check_foundation.py tests/test_foundation.py
git commit -m "test: define monorepo foundation boundary checks"
```

### Task 2：建立根级治理和目标结构

当时计划创建：

```text
README.md
AGENTS.md
.gitignore
apps/dashboard/README.md
packages/research-core/README.md
packages/niu-men-line-strategy/README.md
docs/migration/README.md
docs/migration/source-commits.md
pyproject.toml
.github/workflows/foundation.yml
```

- [ ] Step 1：增加根 README 和协作规则

根文档需要明确：

- 当前仓库是集成 monorepo
- 源仓库仍独立运行
- 原始数据与外部基础设施不进入本仓库
- `research_snapshot.v2` 兼容要求
- 每个迁移阶段使用独立 worktree、branch 和 PR

- [ ] Step 2：增加三个边界 README

M0 时三个目录都只是目标位置：

```text
apps/dashboard/
packages/research-core/
packages/niu-men-line-strategy/
```

这些 README 用于声明所有权，不包含实现代码。

- [ ] Step 3：记录迁移源 commit

首次基准：

| 来源 | 仓库 | Commit |
| --- | --- | --- |
| Dashboard | `runchengxie/wu-t0-trading-dashboard` | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` |
| Niu Men | `runchengxie/niu-men-line-strategy` | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` |

同时记录 `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 有意排除。

- [ ] Step 4：增加安全 ignore 规则

M0 需要至少忽略：

```gitignore
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
```

后续维护已经继续扩展这些规则，例如图片导出的 `artifacts/charts/`。

- [ ] Step 5：建立根 Python 元数据和最小 workflow

M0 根项目只需要 pytest 开发依赖，`uv` 配置为 `package = false`。

最初设计曾计划让 foundation workflow 在 pull request 和 `main` push 时自动运行。仓库后来因为 GitHub Actions 配额策略改成只允许 `workflow_dispatch` 手动触发。这个变化属于后续治理决策，当前配置以 `.github/workflows/foundation.yml` 为准。

- [ ] Step 6：运行结构检查

```bash
uv run --extra dev pytest tests/test_foundation.py -q
uv run python scripts/check_foundation.py
```

- [ ] Step 7：提交基础文档和元数据

```bash
git add README.md AGENTS.md .gitignore apps packages docs/migration pyproject.toml .github/workflows/foundation.yml
git commit -m "docs: add monorepo foundation boundaries"
```

### Task 3：生成 lockfile 并验证基础

- [ ] Step 1：生成根 `uv.lock`

```bash
uv lock
uv run --extra dev pytest tests/test_foundation.py -q
```

- [ ] Step 2：完整验证

```bash
uv run --extra dev pytest -q
uv run python scripts/check_foundation.py
git diff --check
```

- [ ] Step 3：提交 lockfile

```bash
git add uv.lock
git commit -m "build: lock monorepo foundation dependencies"
```

### Task 4：审查 M0 并更新 PR #1

- [ ] Step 1：确认仓库只有基础文件

```bash
git status --short
git ls-files | sort
```

当时必须确认没有 Dashboard、Niu Men 实现、原始 OOS、数据目录或凭据。

- [ ] Step 2：最终验证

```bash
uv run --extra dev pytest -q
uv run python scripts/check_foundation.py
git diff --check
```

- [ ] Step 3：推送 M0 分支

```bash
git push origin feat/monorepo-foundation
```

- [ ] Step 4：更新 PR #1

PR 说明需要强调 M0 只建立基础，源码导入有意延后，并附上实际验证结果。

## M0 后续工作

当时明确拆出的后续阶段：

1. Dashboard 保留历史导入到 `apps/dashboard/`。
2. Niu Men 保留历史导入到 `packages/niu-men-line-strategy/`。
3. M2 抽取 `research-core` 契约和 provenance 资产。
4. M3 处理 Python package 与运行时收敛。
5. M4 完善 CI、artifact handoff 和 release cutover。

## 当前结果

M0 已完成，Dashboard 的 M1 也已经完成。Niu Men、M2 共享契约和完整 release cutover 仍是后续工作。

当前根级 CI、Dashboard 部署和质量检查已经在 M0 最小版本基础上继续演进，因此日常维护应以现行 workflow 和 `AGENTS.md` 为准。
