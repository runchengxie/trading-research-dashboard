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
- 后续将 Niu Men 以独立 PR 导入 `packages/niu-men-line-strategy/`
- 尽量保留可追溯 Git 历史和迁移期兼容入口
- 不在导入过程中顺便重写策略逻辑或研究契约

当前状态：

- Dashboard 已导入并由 monorepo 维护、测试和部署
- Niu Men 仍在独立仓库维护，尚未导入
- 当前仓库没有 Git submodule 或 gitlink

Dashboard 首次导入的精确边界和审计记录见 [Dashboard 导入记录](dashboard-import.md)。

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

当前 `packages/research-core/` 仍是目标位置说明，M2 尚未完成。

## M3：Python 包和运行时收敛

这一阶段计划进一步明确包依赖和运行入口，例如：

```text
apps/dashboard -> packages/research-core
packages/niu-men-line-strategy -> packages/research-core
```

迁移期通过 `sys.path` 或兼容 wrapper 保留的入口，应在确认没有调用方后逐步删除。

Dashboard 当前已经使用 `src/trading_research/` 包结构，但 R-Breaker 等历史模块还有重复数据访问逻辑，后续适合在独立重构中收敛。

## M4：CI 和发布切换

目标包括：

- 更完整的路径感知验证
- producer 与 consumer 的共享契约测试
- 稳定的研究快照发布流程
- Dashboard 数据生成、前端构建、部署和部署后检查
- 明确旧仓库何时转为兼容镜像或归档

当前 monorepo 已经可以从本仓库构建和部署 Dashboard，根级 Actions 仍按仓库配额策略保持手动触发。Niu Men 的发布与完整 monorepo release cutover 尚未完成。

## 当前权威边界

截至当前状态：

- Dashboard 代码、测试、Web 构建和 Workers 部署由本 monorepo 维护
- Niu Men 研究代码仍由独立 `niu-men-line-strategy` 仓库维护
- `research-workspace`、`market-data-platform`、`etf-minute-fetcher` 继续作为外部基础设施
- monorepo 还没有完成整个研究平台的一次性运行时切换

这个边界比简单写成 monorepo 是或不是唯一 source of truth 更准确，因为不同组件目前处在不同迁移阶段。

## 参考文档

- [monorepo 设计](../superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md)
- [根级基础实施计划](../superpowers/plans/2026-08-26-monorepo-foundation.md)
- [Dashboard 导入记录](dashboard-import.md)
- [首次导入源 commit](source-commits.md)
- [当前维护加固计划](../superpowers/plans/2026-08-26-maintenance-hardening.md)
