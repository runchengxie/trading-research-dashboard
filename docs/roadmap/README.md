# 项目路线图

本文记录 A 股交易研究平台尚未完成的主要工作，帮助维护者了解当前进度、实施顺序和验收标准。

当前仓库已经可以构建和部署 Dashboard，也支持静态行情快照、策略研究展示和 PNG 图表导出。Niu Men 策略源码和共享研究包 `research-core` 已进入 monorepo，实时行情服务和完整运行时切换仍在后续阶段。

## 当前状态总览

| 阶段 | 工作内容 | 状态 | 当前说明 |
| --- | --- | --- | --- |
| M0 | monorepo 基础和协作规则 | 已完成 | 根目录治理、目录边界和手动质量检查已经建立 |
| M1 | Dashboard 历史导入 | 已完成 | 代码位于 `apps/dashboard/`，由本仓库构建和部署 |
| M1 | Niu Men 历史导入 | 已完成 | 源提交 `1be7f725` 的过滤历史位于 `packages/niu-men-line-strategy/`；生产运行仍在旧仓库，等待 cutover |
| M2 | `research-core` 共享包 | 已实现 | canonical schema、fixture 和校验工具位于 `packages/research-core/`；workspace 统一留给 M3 |
| M2 | 跨策略快照契约 | 部分完成 | Dashboard 有通用前端模型，wire-level 契约仍以 Niu Men v2 为主 |
| M3 | Python workspace 和 package 依赖 | 已实现 | 根 `[tool.uv.workspace]` 统一三个成员，根 `uv.lock` 是唯一锁文件；Niu Men 已通过 workspace 依赖接入 `research-core` |
| M4 | Niu Men 快照自动发布 | 部分完成 | Niu Men 有独立发布基础，写入 monorepo 的完整链路尚未建立 |
| M5 | 实时行情服务 | roadmap | 当前只有静态快照生成，没有常驻采集服务或 WebSocket |
| M6 | runtime cutover | 待执行 | 需要经过稳定运行验证后再切换旧仓库的生产职责 |

## 已完成能力

以下能力已经在 `main` 中可用：

- Dashboard 位于 `apps/dashboard/`
- 盘前概览、日内工作台和策略研究三个一级区域
- 宝莱特 `sz300246` 作为当前默认标的
- 日线、分时、ATR、VWAP、ORB、KMeans 支撑阻力和交易风格展示
- 静态 `data.json` 和可选的 `research.json` 发布基线
- Niu Men `research_snapshot.v1/v2` 的前端解析和兼容处理
- R-Breaker 入口和历史回测模块
- Cloudflare Workers Static Assets 部署
- Playwright PNG 图表导出和 `trading_research.chart_export.v1` manifest
- 静态资产校验、部署后检查、前端测试、Python 测试和依赖审计
- GitHub Actions 手动触发流程

图表导出和行情能力的详细说明见 [行情与图表导出能力](../capabilities/market-data-and-chart-export.md)。

## 后续阶段

### M1：导入 Niu Men 源码（已完成）

`runchengxie/niu-men-line-strategy` 在源提交 `1be7f725772fa824ce34e2bb833867cb4c3e9fcb` 的批准边界已经以保留历史方式导入 `packages/niu-men-line-strategy/`。导入经过 `git-filter-repo` 过滤、保护路径审计和完整质量门槛验证，细节见 [Niu Men 导入记录](../migration/niu-men-import.md)。

runtime authority 仍在旧仓库；生产运行和快照发布的切换属于 M6。

### M2：实现 `research-core`（已实现）

canonical 契约资产和校验工具位于 `packages/research-core/`：

- JSON Schema：`src/research_core/schemas/research-snapshot.schema.json`
- fixture：`tests/fixtures/research_snapshot/`
- 结构校验：`validate_snapshot()` / `load_snapshot()`
- provenance 规则：`missing_provenance_fields()` / `provenance_complete()` / `validate_provenance_consistency()`

根目录、Dashboard 和 Niu Men 保留兼容镜像，由 `tests/test_research_contract_sync.py` 防漂移。线协议保持 `niu_men.research_snapshot.v2` 不变。

注意：Niu Men 和 Dashboard 的 Python 代码尚未 import `research_core`，本地 package 依赖统一属于 M3 workspace 工作。

### M2：建立跨策略快照契约

Dashboard 当前已经有前端通用 `StrategySnapshot` 模型，但它还不是完整的 wire-level 通用协议。

后续目标：

1. 定义通用快照 envelope、策略身份、时间信息、指标、质量和 provenance 字段。
2. 保留 Niu Men v2 adapter，兼容已有 `research.json`。
3. 为 R-Breaker 和其他策略增加独立 adapter。
4. 让研究页面只依赖注册表和通用模型，不读取策略专用字段。
5. 增加跨策略 fixture 和 schema 测试。

### M3：统一 Python workspace（已实现）

根 `pyproject.toml` 声明 uv workspace，成员包括：

```text
apps/dashboard
packages/research-core
packages/niu-men-line-strategy
```

已完成：

- 根 `uv.lock` 是唯一锁文件，嵌套的 Dashboard 锁文件已删除
- Niu Men 通过 `{ workspace = true }` 本地源依赖 `research-core`，`scripts/snapshot_contract.py` 收敛为兼容 wrapper，生产代码真正 import 共享包
- 成员 Python 版本均为 `>=3.11`
- 根级命令覆盖成员测试、lint、类型检查和依赖审计

保留的兼容入口：Niu Men 的 `scripts/publish_dashboard_snapshot.py` 等直接执行脚本仍使用仓库内 `sys.path` 注入导入同包模块，属于兼容 CLI 行为，待调用方审计后再收敛。

### M4：自动发布研究快照

目标链路：

```text
Niu Men producer
        ↓
research-core 校验
        ↓
apps/dashboard/web/public/research.json
        ↓
自动创建 PR
        ↓
手动质量检查和部署
```

发布流程需要明确研究输入的传递方式。不能依赖 GitHub runner 上不存在的本地 OOS 路径，也不能把原始研究数据或凭据提交到 monorepo。

验收标准：

- 产物来源、研究日期、代码版本和输入摘要写入 provenance
- 缺少必要输入时发布失败
- 快照 schema 校验失败时不创建可合并的更新
- Dashboard 可以继续使用上一份有效快照
- 发布过程不写入旧 Dashboard 仓库

### M5：实时行情服务

实时行情目前只是 roadmap。后续应单独建设：

- 统一 Quote、Bar、MarketStatus 和 freshness 契约
- 可替换的数据源 adapter
- 限频、重试、来源切换和健康状态
- 常驻采集进程
- Redis 最新状态缓存
- FastAPI 或其他服务接口
- WebSocket 推送
- 静态快照降级入口

服务稳定前，Dashboard 继续使用静态 `data.json`。详细说明见 [行情与图表导出能力](../capabilities/market-data-and-chart-export.md)。

### M6：runtime cutover

runtime cutover 需要在多个发布周期稳定运行后进行：

1. 确认 monorepo 能独立生成和部署 Dashboard。
2. 确认研究快照发布链路连续运行。
3. 记录旧 Dashboard 和 Niu Men 仓库的最后可回滚版本。
4. 停止旧仓库向生产路径写入。
5. 观察一段时间后，再决定旧仓库是保留、只读还是归档。

旧仓库不能因为一次成功部署就立即删除。

## 明确暂不做的事情

- 不把 `research-workspace`、`market-data-platform` 或 `etf-minute-fetcher` 作为 Git submodule 引入。
- 不把原始行情和完整 OOS 产物提交到 monorepo。
- 不在 Niu Men 导入阶段修改策略逻辑。
- 不在实时行情服务完成前把静态 JSON 称为实时 API。
- 不在没有稳定回滚点前停用旧仓库。

## 相关文档

- [迁移路线图](../migration/README.md)
- [项目结构说明](../architecture/project-structure.md)
- [Niu Men 导入记录](../migration/niu-men-import.md)
- [行情与图表导出能力](../capabilities/market-data-and-chart-export.md)
- [研究快照](../../apps/dashboard/docs/research-snapshot.md)
