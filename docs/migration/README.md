# 迁移路线图

A 股交易研究平台采用分阶段迁移方式，每个阶段都应通过独立 PR 审查，避免把历史导入、包结构调整、运行时切换和发布流程混成一次难以回滚的大改动。

## M0：monorepo 基础

目标：

- 建立根级治理规则和目标目录
- 记录源仓库与迁移边界
- 建立结构检查和最小 CI
- 明确外部基础设施不进入当前仓库

这一阶段已经完成。

## M1：保留历史的源码导入

目标：

- 将 Dashboard 导入 `apps/dashboard/`
- 将 Niu Men 以独立 PR 导入 `packages/niu-men-line-strategy/`
- 尽量保留可追溯 Git 历史和迁移期兼容入口
- 不在导入过程中顺便重写策略逻辑或研究契约

当前状态：

- Dashboard 已导入并由 monorepo 维护、测试和部署
- Niu Men 已从源提交 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` 完成保留历史的首批导入：策略源码、脚本、测试、schema、pyproject 和批准的文档已进入 `packages/niu-men-line-strategy/`
- 导入历史经过过滤审计，`artifacts/`、研究结果文档、源 CI、源 `uv.lock` 和敏感文件不在新增历史中
- runtime authority 仍在旧仓库；旧 Niu Men 仓库在 cutover 前继续可独立运行
- 当前仓库没有 Git submodule 或 gitlink

首次导入的精确边界和审计记录见：

- [Dashboard 导入记录](dashboard-import.md)
- [Niu Men 导入记录](niu-men-import.md)

## M2：共享契约抽取

计划把研究快照的共享资产逐步迁移到：

```text
packages/research-core/
```

主要包括：

- JSON Schema
- 合同 fixture
- provenance 规则
- 小型、语言中立的校验工具

需要保持：

```text
niu_men.research_snapshot.v2
```

线协议兼容。

当前 `packages/research-core/` 仍是目标位置说明，M2 尚未完成。M2 实现应等待 Niu Men M1 导入通过审查并合入，避免在同一阶段同时处理历史迁移和共享契约抽取。

## M3：Python 包和运行时收敛

这一阶段计划进一步明确包依赖和运行入口，例如：

```text
apps/dashboard -> packages/research-core
packages/niu-men-line-strategy -> packages/research-core
```

迁移期通过 `sys.path` 或兼容 wrapper 保留的入口，应在确认没有调用方后逐步删除。

Dashboard 当前已经使用 `src/trading_research/` 包结构，但 R-Breaker 等历史模块还有重复数据访问逻辑，后续适合在独立重构中收敛。根 `pyproject.toml` 目前也还没有建立统一 uv workspace，这项工作继续留在 M3。

## M4：CI 和发布切换

目标包括：

- 更完整的路径感知验证
- producer 与 consumer 的共享契约测试
- 稳定的研究快照发布流程
- Dashboard 数据生成、前端构建、部署和部署后检查
- 明确旧仓库何时转为兼容镜像或归档

当前 monorepo 已经可以从本仓库构建和部署 Dashboard，根级 Actions 仍按仓库配额策略保持手动触发。旧 Niu Men 仓库已经具有手动快照发布能力，但迁入 monorepo、共享契约接入和完整 release cutover 尚未完成。

## 当前权威边界

截至当前状态：

- Dashboard 代码、测试、Web 构建和 Workers 部署由本 monorepo 维护
- Niu Men 研究代码已通过 M1 导入进入本仓库，但生产运行和快照发布仍在旧 `niu-men-line-strategy` 仓库执行，直到 runtime cutover 完成
- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 继续作为外部基础设施
- monorepo 还没有完成整个研究平台的一次性运行时切换

实时行情的现状和建设路线见 [行情与图表导出能力](../capabilities/market-data-and-chart-export.md)。图表 PNG 导出已经实现，实时行情服务仍属于 roadmap。

## 最近完成的维护

PR #7 已于 2026 年 8 月 26 日合并到 `main`，合并提交为 `7bd3740`。本次维护更新了 Dashboard 的 Python 锁文件，清除了 `pip-audit` 报告的已知漏洞，补充了静态资产和部署检查，完善了前端测试与构建流程，并加入了 PNG 图表导出。

当前 Python 依赖审计结果为 0 个已知漏洞。GitHub Actions 仍只允许通过 `workflow_dispatch` 手动触发，原因是仓库需要控制 Actions 配额。

这个边界比简单写成 monorepo 是或不是唯一 source of truth 更准确，因为不同组件目前处在不同迁移阶段。

## 参考文档

- [monorepo 设计](../superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md)
- [根级基础实施计划](../superpowers/plans/2026-08-26-monorepo-foundation.md)
- [Dashboard 导入记录](dashboard-import.md)
- [Niu Men 导入记录](niu-men-import.md)
- [Niu Men M1 实施计划](../superpowers/plans/2026-08-26-m1-niu-men-import.md)
- [首次导入源 commit](source-commits.md)
- [当前维护加固计划](../superpowers/plans/2026-08-26-maintenance-hardening.md)
