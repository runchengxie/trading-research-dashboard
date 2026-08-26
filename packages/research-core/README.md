# Research Core

`packages/research-core/` 是后续共享研究契约的目标位置。

计划承担：

- 研究快照 JSON Schema
- producer 与 consumer 共用的 fixture
- provenance 字段和校验规则
- 少量与策略实现无关的共享校验工具

这里不应放入：

- Niu Men 指标和信号逻辑
- R-Breaker 策略实现
- Dashboard React 组件
- 行情抓取和本地数据归档
- 完整 OOS 研究产物

当前 M2 尚未完成，这个目录仍是边界占位。现阶段 Niu Men 独立仓库仍是 `niu_men.research_snapshot.v2` 的规范 producer，Dashboard 在 `apps/dashboard/` 保留 consumer 侧 schema 和 fixture 副本。

后续抽取时需要保持 `niu_men.research_snapshot.v2` 线协议兼容，并在删除重复资产前先让 producer 和 consumer 都通过共享契约测试。
