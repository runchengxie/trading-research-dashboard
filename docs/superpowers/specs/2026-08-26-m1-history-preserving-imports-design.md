# M1 保留历史导入设计

## 状态

本设计于 2026-08-26 批准，用于规划私有 `a-share-trading-research` monorepo 的第一阶段源码迁移。

这是一份 M1 设计历史。当前 Dashboard 已完成导入，Niu Men 尚未导入，实际进度见 `docs/migration/README.md`。

## 目标

把 Dashboard 和 Niu Men 的当前实现迁入批准的 monorepo 位置，同时尽量保留有价值的 Git 历史，并确保原始行情、生成型研究产物、凭据和受限材料不进入 monorepo 历史。

M1 原计划拆成两个可以独立审查的 PR：

1. Dashboard 导入 `apps/dashboard/`。
2. Niu Men 导入 `packages/niu-men-line-strategy/`。

源仓库在 M1 期间保持可独立使用。

## 边界

以下项目继续留在 monorepo 之外：

- `research-workspace`
- `market-data-platform`
- `etf-minute-fetcher`

M1 不负责抽取 `research-core`，不负责统一全部 Python 包依赖，也不改写 Niu Men 策略逻辑。这些工作属于后续阶段。

## 源快照

首次迁移选择的精确源 commit 记录在 `docs/migration/source-commits.md`：

| 来源 | Commit | 目标位置 |
| --- | --- | --- |
| `wu-t0-trading-dashboard` | `8f809f58b2cdb4b6c6dee8e8d4c767a6ea30a114` | `apps/dashboard/` |
| `niu-men-line-strategy` | `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` | `packages/niu-men-line-strategy/` |

每次导入记录都需要说明：

- 源仓库
- 精确源 commit
- 目标路径前缀
- 路径过滤规则
- 显式排除路径

这样审查者可以复现首次导入结果。

## 导入方式

每个源项目都应在隔离的临时 clone 或 worktree 中处理：

1. 从精确源 commit 开始。
2. 使用支持历史重写的路径过滤方式，只把选择的路径改写到目标前缀。
3. 保护路径需要从重写后的历史中排除，不能只在最终 checkout 删除。
4. 将过滤后的历史合入迁移分支，必要时允许 unrelated histories。
5. 删除临时 remote，并确认 monorepo 中没有 submodule 或 gitlink。

M1 的核心要求是让受保护文件完全不进入导入历史。只清理当前工作树达不到这个目的。

## Dashboard 导入契约

首次 Dashboard 导入允许以下路径进入 `apps/dashboard/`：

- `src/`
- `web/`，排除生成的 `web/public/data.json` 和 `web/public/research.json`
- `backtest/`
- `tests/`
- `scripts/`
- `docs/backtest.md`
- `docs/cloudflare-workers.md`
- `docs/configuration.md`
- `docs/data-sources.md`
- `docs/indicators.md`
- `docs/outputs.md`
- `docs/research-snapshot.md`
- `docs/troubleshooting.md`
- `docs/web-frontend.md`
- `schemas/research-snapshot.schema.json`
- `pyproject.toml`
- `uv.lock`
- `wrangler.jsonc`
- `README.md`
- `.gitignore`

首次导入排除：

- `data/raw/`
- 生成型 Web 数据和研究快照
- `.env*` 与其他凭据
- 本机环境文件和缓存
- 已经有 `src/` 维护版本的历史根级脚本
- 源仓库自己的 CI 文件

首次导入步骤不改变 Dashboard 当时的选中证券、研究新鲜度行为或 `research_snapshot.v2` consumer 语义。

Dashboard M1 已经完成。精确路径映射和实际验证结果见 `docs/migration/dashboard-import.md`。

## Niu Men 导入契约

计划允许以下内容进入 `packages/niu-men-line-strategy/`：

- `src/`
- `scripts/`
- `tests/`
- `schemas/research-snapshot.schema.json`
- `README.md`
- `pyproject.toml`
- `.gitignore`
- 实现和契约相关的维护文档

计划排除：

- `artifacts/`
- OOS CSV、JSON 结果和生成型研究输出
- `docs/original-transcript.md`
- 只记录某次研究结果的 findings 或 portfolio 结果文档
- `.env*`
- 本地数据和缓存
- 源仓库 CI 文件

必须保持：

```text
niu_men.research_snapshot.v2
```

以及现有 provenance、质量警告和策略行为。

当前 Niu Men 尚未导入，因此这部分仍是未来迁移约束。

## monorepo 集成

每个历史导入完成后需要：

- 把 M0 的占位 README 改成准确的包边界说明
- 更新 `docs/migration/source-commits.md`
- 更新根级边界检查和测试
- 让新增源码路径进入明确允许范围，同时继续拒绝受保护路径
- 只做验证导入所必需的根级依赖和 CI 调整
- 不提交 Git submodule 或长期源仓库 remote 配置

M1 不要求根 `pyproject.toml` 立刻变成完整 uv workspace。嵌套项目元数据可以保留，等后续包收敛阶段处理。

## 验收标准

每个导入 PR 需要提供：

1. 跟踪文件审计中没有原始数据、生成 OOS、凭据或 gitlink。
2. 受保护路径从导入历史中消失的证据。
3. 代表性文件的 `git log --follow` 证据。
4. 被导入包原有的 Python 测试，以及 Dashboard Web 单元测试和构建验证。
5. 更新后的 monorepo foundation checker 通过。
6. 原始源仓库工作树没有被迁移操作污染。
7. `research_snapshot.v2` 和 Niu Men 策略逻辑保持不变。

## 顺序

Dashboard 先导入，因为它是主要应用边界。Niu Men 应基于更新后的 `main` 通过独立 PR 导入。

只有两个包都稳定后，才进入 M2，把共享契约抽取到 `packages/research-core`。

当前实际状态正好停在这个顺序的中间：Dashboard 已进入 monorepo，Niu Men 仍等待独立迁移。
