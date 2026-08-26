# Niu Men M1 导入记录

## 状态

Niu Men M1 正在准备历史保留导入。本文件记录已经批准的源提交、路径映射、排除边界、回滚点和后续验证要求。

当前分支只完成迁移计划与清单准备，尚未执行 `git-filter-repo` 历史重写，也没有宣称 Niu Men 已进入 monorepo runtime。真正的历史合入必须在独立 Git worktree 中完成，并通过本文件列出的历史审计与测试门槛。

## 源与回滚点

| 字段 | 值 |
| --- | --- |
| 源仓库 | `runchengxie/niu-men-line-strategy` |
| 精确源 commit | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` |
| 目标前缀 | `packages/niu-men-line-strategy/` |
| 导入方式 | 从精确源 commit 构造历史过滤仓库，再通过 unrelated-history merge 合入独立迁移分支 |

该源 commit 当前对应 Niu Men 已稳定 `niu_men.research_snapshot.v2` 合同后的 `main` 基线，是本次首次导入的 rollback point。

## 允许路径映射

以下路径是 M1 Niu Men 导入的完整允许集合：

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

`src/`、`scripts/`、`tests/` 递归包含其正常源码和测试内容，但仍受下方敏感路径与文件名规则约束。

## 明确排除

以下内容不得进入 monorepo 的最终树或由本次导入新增的 Git 历史：

- `artifacts/**`
- 完整 OOS CSV/JSON 与其他生成研究输出
- `docs/original-transcript.md`
- `docs/research-findings-*.md`
- `docs/portfolio-oos-research-*.md`
- `docs/superpowers/**`
- `.github/**`
- 源仓库 `uv.lock`
- 任意 `.env*`
- 文件名包含 `credential`、`secret`、`token`、`password` 的敏感文件
- `*.pem`、`*.key`、`*.p12`、`*.pfx`
- 原始行情、本地缓存和仅适用于单机的数据目录

这些排除必须应用到重写历史，不能只在最终 checkout 中删除。导入完成后需要使用 `git log --all --name-only` 对受保护路径进行确定性查询。

## M1 行为边界

本次导入只迁移所有权和可追溯历史，不改变以下语义：

- Niu Men 指标、信号、回测、组合和 walk-forward 逻辑
- bar `t` 信息与 bar `t+1` 执行时序约束
- `niu_men.research_snapshot.v2` wire version
- provenance 字段与 `quality.status` / warning 语义
- 当前外部 `market-data-platform`、`etf-minute-fetcher`、`research-workspace` 边界
- 旧 Niu Men 仓库在 runtime cutover 之前继续可独立运行

M1 不抽取 `packages/research-core`，不创建根 uv workspace，也不把旧仓库改成只读镜像。以上工作分别属于后续迁移阶段。

## Foundation 接入要求

导入完成后，根级 foundation checker 只允许以下 Niu Men 目录前缀：

```text
packages/niu-men-line-strategy/src/
packages/niu-men-line-strategy/scripts/
packages/niu-men-line-strategy/tests/
```

根级文件和 docs/schema 继续按精确 allowlist 接受。以下代表性路径必须保持拒绝：

```text
packages/niu-men-line-strategy/artifacts/result.json
packages/niu-men-line-strategy/.github/workflows/ci.yml
packages/niu-men-line-strategy/docs/original-transcript.md
packages/niu-men-line-strategy/uv.lock
packages/niu-men-line-strategy/.env
```

## 验证门槛

### 历史审计

导入完成后至少记录：

```bash
git log --follow --oneline -- packages/niu-men-line-strategy/src/niu_men_line_strategy/signals.py | head -20
git ls-files --stage | awk '$1 == "160000" {print}'
git submodule status
git diff --check
```

代表性 `git log --follow` 必须能到达源仓库历史；gitlink 和 submodule 输出必须为空。

### Niu Men 源质量门槛

M1 设计不提交 Niu Men 的嵌套 `uv.lock`，因此执行验证时可临时复制精确源提交的 lockfile，运行完成后必须删除且不得纳入提交。

需要通过：

```bash
uv run --locked --extra dev pytest
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev ty check src
uv run --locked --extra dev coverage run -m pytest
uv run --locked --extra dev coverage report --fail-under=80
uv run --locked --extra dev pip-audit --skip-editable
```

### Monorepo 回归门槛

还需要重新运行根项目、Dashboard、前端和 foundation 的完整质量检查。精确命令记录在：

```text
docs/superpowers/plans/2026-08-26-m1-niu-men-import.md
```

## 当前执行记录

已经完成：

- 核实源仓库与精确源 commit
- 核实源 commit 包含当前 Niu Men 源码、测试、schema 和快照发布能力
- 核实 monorepo 的目标目录目前仍是 README 占位
- 建立独立迁移分支
- 写入 M1 Niu Men 实施计划
- 写入本导入清单

尚未执行：

- `git-filter-repo` 历史重写
- unrelated-history merge
- foundation allowlist 代码与测试修改
- Niu Men 源测试、lint、type、coverage、pip-audit
- 完整 monorepo 回归
- runtime cutover

在上述证据齐全前，本迁移 PR 应保持 Draft。
