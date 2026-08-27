# trading-research-dashboard monorepo 设计

## 状态

这是初始 monorepo 基础阶段已经批准的设计文档。它记录仓库边界和迁移顺序。文档编写时尚未开始源码导入，因此其中部分状态描述属于当时的设计背景。当前实际进度以 `docs/migration/README.md` 和各组件现行文档为准。

## 目标

建立 `trading-research-dashboard` 的私有集成仓库，并在迁移期间保留 `wu-t0-trading-dashboard` 与 `niu-men-line-strategy` 独立运行和回滚的能力。

## 背景

两个原有仓库已经在公开契约层形成明确分工：

- Dashboard 消费版本化的 `niu_men.research_snapshot.v2` JSON。
- Niu Men 负责研究执行、OOS 计算、provenance、schema 校验和研究快照生成。
- Dashboard 负责行情视图、前端渲染、研究缺失时的降级和 consumer 侧契约检查。
- 行情平台与分钟数据 fetcher 继续作为外部基础设施，通过稳定的数据或文件契约接入。

因此 monorepo 的第一步是建立清晰的集成层和迁移边界，避免在一次操作里同时重写两个成熟项目。

## 仓库边界

仓库保持私有。`research-workspace` 不属于这里，行情和分钟数据基础设施也不会复制进入本仓库。

目标结构：

```text
trading-research-dashboard/
├── apps/
│   └── dashboard/
├── packages/
│   ├── research-core/
│   └── niu-men-line-strategy/
├── schemas/
├── docs/
├── scripts/
├── pyproject.toml
└── README.md
```

目标依赖方向：

```text
market-data-platform / etf-minute-fetcher
                 │ 稳定数据契约
                 ▼
          research-core
            │       │
            ▼       ▼
      Niu Men     Dashboard
      producer    consumer
```

`research-core` 只保存语言中立的契约资产和少量共享校验、provenance 工具。这里不放 Niu Men 指标、信号、回测规则，也不放 Dashboard 展示代码。

## 迁移策略

### M0：基础建设

建立私有仓库、根 README、协作规则、目录结构和最小 CI。

这一阶段的设计约束包括：

- 不修改两个源仓库
- 不提前宣称整个 monorepo 已经成为全部组件的唯一运行来源
- 先把所有权和安全边界写清楚

当前 M0 已完成。

### M1：保留历史的导入

计划将源仓库导入目标子目录，并尽量保留可追溯 Git 历史：

```text
wu-t0-trading-dashboard  -> apps/dashboard/
niu-men-line-strategy    -> packages/niu-men-line-strategy/
```

首次导入允许临时保留兼容入口和既有内部目录，但不得在导入步骤里悄悄重写策略逻辑或改变研究快照线协议。

每次导入都需要记录：

- 源仓库
- 精确源 commit
- 路径过滤边界
- 排除项
- 回滚和验证证据

当前 Dashboard 已完成导入。Niu Men 仍在独立仓库维护，尚未进入本 monorepo。

### M2：共享契约抽取

把规范研究快照 schema、fixture 和 provenance 规则迁移到：

```text
packages/research-core/
```

必要不变量：

- 线版本继续保持 `niu_men.research_snapshot.v2`
- 抽取验证完成前，Niu Men 继续承担 producer 和 schema 规范来源角色
- Dashboard 始终把研究数据视为可选输入
- provenance 缺失或不完整必须显式展示
- Dashboard 不 import Niu Men 实现模块

删除重复副本前，应先建立 package 级共享契约测试，让 producer 和 consumer 都针对共享资产通过验证。

当前 M2 已完成；本段保留初始设计阶段的历史状态说明。

### M3：Python 包和运行时收敛

统一 Python 3.11 或更高版本，并使用明确的本地 package 依赖代替长期 `sys.path` 兼容技巧。

目标关系：

```text
apps/dashboard                -> packages/research-core
packages/niu-men-line-strategy -> packages/research-core
```

迁移期兼容 CLI wrapper 可以短期保留，新代码应使用包路径。兼容入口应在确认外部调用方已经迁移后单独删除。

把这一阶段与源码导入分开，可以避免 Python 版本、依赖和包装问题与 Git 历史迁移问题相互干扰。

### M4：CI 与发布切换

完整 monorepo 发布体系最终需要覆盖：

1. 校验 `research-core` 契约。
2. 运行 Niu Men producer 测试和快照验证。
3. 运行 Dashboard Python、Web 测试与生产构建。
4. 发布可审查的 Dashboard 研究快照更新。
5. 让外部行情输入和凭据始终留在 Git 历史之外。

只有经历稳定发布周期后，才适合讨论将原仓库转成兼容镜像或归档。这个决定需要独立审查。

当前 monorepo 已经可以维护并部署 Dashboard，但 Niu Men 和共享契约的完整 release cutover 尚未完成。

## 数据和产物策略

以下内容不得提交到 monorepo：

- 原始行情
- 完整 OOS CSV
- 凭据
- 本机绝对数据目录
- 外部数据平台目录
- 仅用于临时自动化的图片和运行时缓存

仓库可以保存：

- schema
- 小型测试 fixture
- manifest
- 经过审查的版本化研究快照契约资产
- 不暴露本机路径或受限源材料的可复现元数据

Parquet 和 manifest 继续作为行情基础设施的集成边界。GitHub runner 不应假定可以访问开发机上的 `DATA_PLATFORM_ROOT`。

## 兼容与回滚

每个迁移阶段使用独立 PR。

迁移期间：

- 尚未迁移的源仓库继续独立构建和测试
- 不引入 Git submodule 或 gitlink
- 不做破坏性仓库删除
- 归档旧仓库需要单独决策
- 失败的迁移 PR 可以关闭，不影响独立源仓库的已知可用 `main`

Dashboard 完成 M1 后，其代码和 Workers 部署已经转由 monorepo 维护。Niu Men 仍维持独立 producer 身份，这两个组件当前处于不同迁移阶段。

## 初始成功标准

基础阶段完成标准：

1. 私有仓库具备明确目标结构。
2. 明确排除 `research-workspace` 和行情基础设施。
3. 根级检查可以验证仓库结构和关键文档。
4. 迁移计划记录每个源项目的基准 commit 和回滚点。
5. 基础阶段本身不偷偷复制或修改业务实现。

这些 M0 条件已经满足。

## 初始非目标

基础阶段不负责：

- 把 Dashboard 和 Niu Men 合成一个 Python package
- 修改 Niu Men 策略逻辑或研究结果
- 重写 Dashboard UI
- 改变 `research_snapshot.v2`
- 迁移 `research-workspace`
- 搬迁行情存储或 fetcher
- 归档或删除源仓库
- 宣称整个 monorepo 在第一阶段就已经具备完整生产切换能力

后续维护可以在不破坏上述边界的前提下继续改进 Dashboard，例如修复数据语义、部署流程、质量门槛和图片导出。这类功能演进应通过独立 PR 留下审查记录。
