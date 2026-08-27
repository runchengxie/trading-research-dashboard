# trading-research-dashboard 项目路线图

本文记录 Trading Dashboard 尚未完成的主要工作、实施顺序和验收边界。状态以当前代码和真实运行证据为准；workflow、脚本或 PR 的存在本身不等于生产 gate 已经发生。

## 当前状态总览

| 阶段 | 工作内容 | 状态 | 当前说明 |
| --- | --- | --- | --- |
| M0 | monorepo 基础和协作规则 | 已完成 | 根目录治理、目录边界、手动质量检查和独立 PR/worktree 规则已建立 |
| M1 | Dashboard 历史导入 | 已完成 | 代码位于 `apps/dashboard/`，由本仓库构建和部署 |
| M1 | Niu Men 历史导入 | 已完成 | 源码、测试和 producer 位于 `packages/niu-men-line-strategy/`；旧仓库 runtime authority 等待 M6 freeze |
| M2 | `research-core` 共享包 | 已完成 | canonical Niu Men contract、generic strategy snapshot、fixture 和校验工具已进入共享包 |
| M2b | 跨策略快照契约 | 已完成 | `trading_research.strategy_snapshot.v1` 已落地，Niu Men 保留旧 wire adapter，R-Breaker 有 generic producer/consumer |
| M3 | Python workspace 和 package 依赖 | 已完成 | 根 `uv.lock` 是唯一锁文件，成员通过 uv workspace 统一解析 |
| M4 | 研究快照自动发布 | 代码链路完成，证据待补 | Niu Men publisher 与 R-Breaker artifact→generator→独立 snapshot PR 链路均已进入 `main`；仍需至少一次真实 R-Breaker publication 证据 |
| M5 | 实时行情服务 | 部分完成 | 港股兼容、Alpaca 美股实时、US daily/1-minute history、Redis latest state/PubSub/heartbeat primitives 已进入 `main`；Redis runtime wiring、readiness 与生产故障验证未完成 |
| M6 | runtime cutover | shadow 实现已合并，观察中 | scheduled mode 仍为 `shadow`，需要真实 5 个连续交易日、人工对比、publication 和 authoritative cutover 证据 |
| M6b | legacy freeze / retirement | 被 M6 阻塞 | freeze PR 已准备；archive 必须等待 cutover、observation、no-write 和 caller audit |

## 已完成能力

当前 `main` 已具备：

- Dashboard 位于 `apps/dashboard/`
- 盘前概览、日内工作台和策略研究三个一级区域
- editorial research UI：暖白/深色研究主题、分隔线布局和更克制的 ECharts palette
- A 股/ETF 静态行情链路、港股兼容层和美股历史 bars 接入
- Dashboard 默认标的宝莱特、AAPL、MSFT、NVDA、TSLA；`--codes` 支持显式传入任意带市场标记的美股 ticker
- 日线、分时、ATR、VWAP、ORB、KMeans 支撑阻力和交易风格展示
- `data.json` 静态 fallback
- Niu Men `research_snapshot.v1/v2` parser/adapter
- `trading_research.strategy_snapshot.v1` generic strategy envelope
- R-Breaker 策略、输入 artifact 校验、snapshot generator、前端 registry，以及独立 strategy target publisher/workflow
- Cloudflare Workers Static Assets 部署
- Playwright PNG 图表导出和 `trading_research.chart_export.v1` manifest
- Alpaca 美股实时 collector、内存 QuoteStore、HTTP quote API 和 WebSocket overlay
- Alpaca US daily/1-minute historical provider、`GET /v1/bars/{symbol}` 和 Dashboard `market_compat` 映射
- Redis latest quote、Pub/Sub、collector heartbeat state primitives，以及原子 monotonic quote write
- HK/US market metadata、币种和时区支持
- M6 shadow runtime candidate 校验、runtime manifest 和 evidence artifact
- cross-repository research artifact token gate
- 静态资产校验、部署检查、前端测试、Python 测试和 foundation check

## 下一阶段

### M4：补齐真实多策略发布证据

R-Breaker 生产发布代码链路已经进入 `main`，目标保持为所有策略通过明确 target 发布，不允许一个策略覆盖另一个策略的静态文件。

当前路径：

```text
Niu Men snapshot artifact
        ↓
shared publisher
        ↓
apps/dashboard/web/public/research.json

R-Breaker input artifact
        ↓
R-Breaker artifact validation
        ↓
generate_rbreaker_snapshot
        ↓
trading_research.strategy_snapshot.v1
        ↓
shared publisher (strategy_id=r-breaker)
        ↓
apps/dashboard/web/public/rbreaker-research.json
```

R-Breaker production publication 剩余完成标准：

1. 使用真实 `trading_research.rbreaker_input.v1` artifact，文件大小和 SHA-256 校验通过。
2. generator 产出 generic snapshot 并记录 producer run id 与 input hash。
3. publisher 校验 schema、strategy identity、quality 和 provenance，并只修改 `rbreaker-research.json`。
4. 原始 minute bars 不进入 Git。
5. 至少一次真实 artifact run / publication PR 成功并记录证据后，M4 才能标记为生产证据完成。

### M5：完成实时行情运行时

已经进入 `main` 的能力包括：

- CN/HK/US symbol 与 market metadata
- 港股历史日线和近期分钟兼容层
- Alpaca StockDataStream 美股实时采集
- 当前单实例内存 QuoteStore
- `GET /v1/quotes/{symbol}` 与 WebSocket quote stream
- Dashboard 实时价格 overlay、stale 标记和静态 fallback
- Alpaca US daily/1-minute historical provider 与 `GET /v1/bars/{symbol}`
- Dashboard `market_compat` US daily/minute 映射和缓存 fallback
- Redis latest state、fixed-channel Pub/Sub、collector heartbeat、finite heartbeat TTL
- Redis-side 原子 monotonic quote write 与 subscription failure cleanup

仍未完成：

1. **Redis runtime wiring**：让 collector 写 Redis，并让 REST/API 从 Redis latest state 读取；当前 in-memory `QuoteStore` 仍是实际运行路径。
2. **readiness**：区分 API alive、Redis unavailable、collector stale 和 upstream stale。
3. **WebSocket Redis subscription**：从轮询进程内 store 收敛到 Redis snapshot + Pub/Sub 更新，并验证断线清理和重连 bootstrap。
4. **进程边界**：collector 与 API 按批准设计拆分运行，避免把当前 Alpaca stream thread/event loop 与单个 async Redis client 不安全地跨线程共享。
5. **真实 Redis/provider 验证**：使用实际 Redis server 覆盖 Lua compare-and-set、Redis loss、provider loss、reconnect、stale 和静态 fallback。

静态 `data.json` 在 M5 完整稳定前继续是安全 fallback。

### M6：完成 runtime cutover

shadow workflow 已合并到 `main`，但 production cutover 仍未完成。真实 gate 记录在 [`../operations/runtime-cutover.md`](../operations/runtime-cutover.md)。

切换前必须具备：

1. 5 个连续交易日 scheduled shadow run 成功。
2. 至少 2 次 shadow artifact 与同日旧 production 页面人工核对。
3. research publication 至少 3 个记录周期，并且至少 1 次是真实 publication。
4. cross-repository artifact authentication 有真实成功证据，或生产链路不再依赖该跨仓库下载。
5. 手动 `authoritative` run 完成 candidate generation、validation、build、Cloudflare deploy 和 smoke。
6. production URL 的 data date 与 candidate 一致。

只有上述 gate 满足后才允许：

1. 合并 legacy Dashboard 仓库的 freeze PR #44。
2. 在 monorepo research publication authority 证明后合并 legacy Niu Men 仓库的 freeze PR #22。
3. 独立小 PR 把 scheduled `SCHEDULE_MODE` 从 `shadow` 改为 `authoritative`。
4. 进入 post-cutover 连续交易日 observation。

### M6b：legacy retirement

freeze 与 archive 是两个阶段。

freeze 后旧仓库成为 rollback mirror；真正 archive 还需要：

- M6 post-cutover observation 通过；
- Dashboard/Niu Men 分别满足 no-write 观察窗口；
- GitHub-visible caller audit；
- cron/systemd/Hermes/self-hosted runner/local research runner 等 external caller audit；
- rollback SHA 和 procedure 可验证；
- repository setting 实际变成 archived 后才能记录 `archived`。

在这些条件发生前，文档必须保持 `not-yet-run`、`in-progress` 或具体阻塞原因，不提前写成完成。

## UI 设计改造

editorial research UI 已合并到 `main`。Dashboard 保留自己的业务内容和三段式信息架构，采用暖白研究底色、弱网格、细分隔线、减少圆角/阴影、蓝色结构强调、高密度研究表格以及更克制的 ECharts palette；深色主题和移动端无页面横向溢出已有浏览器回归覆盖。

UI 改造没有引入虚构的行业权重、市场 regime、打分或其他当前数据契约没有的内容，后续 UI 变更继续与 M5/M6 数据和运行时逻辑保持独立 PR 边界。

## 明确暂不做的事情

- 不把 `research-workspace`、`market-data-platform` 或 `etf-minute-fetcher` 作为 Git submodule 引入。
- 不把原始行情、完整 OOS 或 R-Breaker minute artifact 提交到 monorepo。
- 不在 R-Breaker publication PR 中修改策略逻辑或顺手做参数优化。
- 不把实时 tick 当作美股历史 provider。
- 不在没有真实 cutover/rollback 证据前停用或 archive 旧仓库。

## 相关文档

- [项目结构说明](../architecture/project-structure.md)
- [行情与图表导出能力](../capabilities/market-data-and-chart-export.md)
- [Runtime cutover runbook](../operations/runtime-cutover.md)
- [研究快照](../../apps/dashboard/docs/research-snapshot.md)
- [R-Breaker production publication design](../superpowers/specs/2026-08-27-rbreaker-production-publication-design.md)
