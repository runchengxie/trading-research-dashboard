# Runtime and Data Closeout Design

## Goal

收口 `trading-research-dashboard` 的数据目录、实时行情运行链路和生产发布入口，并删除本机不再使用的两个旧项目 checkout。

## Scope

- 本项目自有的 cache、研究 artifact、候选输入和运行输出统一使用 `~/data/trading-research-dashboard`，在当前机器上即 `/path/to/user/data/trading-research-dashboard`。
- `market-data-platform` 与 `etf-minute-fetcher` 继续作为外部原始数据源，不复制或吞并其数据目录。
- 保留现有 Alpaca + Redis 实时行情架构，补齐统一配置、可运行入口、健康检查和测试；不伪造实时数据。
- 新仓库成为唯一正式开发与发布主线；发布 workflow 提供明确的 authoritative 入口，同时保留安全 fallback。
- 删除 `/path/to/user/code/wu-t0-trading-dashboard` 和 `/path/to/user/code/niu-men-line-strategy` 两个本地 checkout。远程 GitHub 仓库不删除。

## Data layout

项目数据根目录通过 `TRADING_RESEARCH_DATA_ROOT` 配置，默认值为 `~/data/trading-research-dashboard`。项目生成数据按以下职责分层：

```text
<root>/
├── cache/       运行时行情缓存
├── artifacts/   研究输入与中间 artifact
├── research/    研究输出与发布候选
├── rbreaker/    R-Breaker 输入和探索产物
└── runtime/     本机运行状态（不提交 Git）
```

外部源目录继续由各自 provider/config 显式指定。仓库内 `apps/dashboard/web/public/*.json` 仍是经过审查、可部署的静态快照，不迁移到数据根目录。

## Runtime behavior

- Alpaca credentials 只在服务端使用；缺少 credentials 时不启动实时 collector。
- `REDIS_URL` 配置后使用 Redis 共享报价、Pub/Sub 和 heartbeat；未配置时使用进程内存，仅作为本地开发模式。
- 历史美股数据可以由 yfinance fallback 提供，但不能被描述为实时行情。
- `/healthz` 检查进程存活，`/readyz` 检查运行依赖和 collector freshness；实时服务失败时 Dashboard 保留静态快照。
- 配置和文档必须明确“代码链路可运行”与“当前环境已有真实实时数据”的区别。

## Production cutover

新仓库的 authoritative workflow 负责生成候选、校验静态资产、构建并在具备部署凭据时部署。旧仓库 workflow 只保留显式确认的 rollback 入口。由于本机没有生产凭据和连续交易日运行证据，本次变更不伪造 cutover 已完成；文档会记录 authoritative 入口已准备、真实生产 gate 仍需外部验证。

## Verification

- 配置单元测试覆盖默认数据根目录、环境变量覆盖和无 Alpaca credentials 时 collector 不启动。
- 运行 Dashboard、market-data-service 和根目录测试/lint/build。
- 检查新仓库工作树和数据目录路径。
- 删除旧 checkout 前确认两个目录均为干净工作树，且新仓库已包含迁移后的代码和回滚说明。

