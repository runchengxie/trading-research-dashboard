# Modern Web/API Foundation Design

## Goal

在不破坏 Dashboard 静态部署和现有行情降级路径的前提下，强化现有 FastAPI 行情服务的 OpenAPI 契约，并让 React 前端通过一个明确的 REST client 使用该服务。为后续 pnpm workspace、OpenAPI TypeScript codegen 和 shadcn/ui 迁移建立稳定边界。

## Current state

- 仓库已经是 uv workspace monorepo。
- `apps/dashboard/web` 使用 React、TypeScript、Vite、ECharts 和 npm。
- Dashboard 主数据、研究数据和策略研究结果仍从静态 JSON 加载。
- `apps/market-data-service` 已使用 FastAPI，并提供 health、ready、quote、bars 和 WebSocket 接口。
- 浏览器已经通过 `VITE_MARKET_DATA_URL` 接入行情 WebSocket，但 REST 返回值目前用无结构的 `dict[str, object]` 表达，因此 OpenAPI 对前端的类型价值有限。
- Dashboard 与行情服务可以跨 origin 部署。WebSocket 已经能跨 origin 工作，但浏览器 REST `fetch` 需要服务端 CORS 策略。

## Scope of this PR

### 1. Typed FastAPI responses

新增 Pydantic response models，覆盖：

- `GET /healthz`
- `GET /readyz`
- `GET /v1/quotes/{symbol}`
- `GET /v1/bars/{symbol}`

现有 WebSocket payload 保持兼容。REST endpoint 显式声明 `response_model`，让 `/openapi.json` 产生稳定、可消费的 schema。

### 2. OpenAPI contract checks

新增测试，确保关键路径存在，并且 quote/bars endpoint 的 200 response 引用命名 schema。测试直接检查 `create_app().openapi()`，不依赖真实 Redis、Alpaca、yfinance 网络请求。

新增 OpenAPI 导出脚本，允许开发者在本地生成 schema 文件，供后续 TypeScript codegen 使用。脚本默认输出到 stdout，也允许写入指定路径；本 PR 不提交由特定 FastAPI 版本生成的大型 schema artifact，避免无意义 diff。

### 3. Frontend REST client boundary

新增一个小型 `marketDataApi.ts`：

- 统一清理 `VITE_MARKET_DATA_URL` 的尾部斜杠。
- 构造 REST URL 时正确编码 symbol。
- 提供 `fetchMarketDataHealth()` 和 `fetchMarketDataQuote()`。
- 返回值做运行时结构校验，拒绝畸形 payload。
- 允许注入 `fetch`，便于 Node 原生单元测试。

Dashboard 继续用静态 `data.json` 作为主要数据源；行情 WebSocket 逻辑不改变。页面只把 REST health 作为服务状态信号，不让 REST 故障拖垮静态 Dashboard。

### 4. Explicit browser CORS allowlist

新增 `MARKET_DATA_CORS_ORIGINS` 配置，只接受逗号分隔的 `http://` / `https://` origin：

- 默认空列表，不额外开放浏览器 REST 跨域访问。
- 明确拒绝 `*`。
- 去掉 origin 尾部 `/`，并去重保序。
- `create_app()` 只在 allowlist 非空时安装 `CORSMiddleware`。
- 只开放当前 REST client 所需的 `GET` 方法，不改变 WebSocket 路径。

`.env.example` 提供本地 Vite origin 示例，部署文档说明生产 Dashboard origin 需要显式加入 allowlist。

### 5. UI behavior

现有“数据正常”状态改为更准确的三态：

- 未配置 `VITE_MARKET_DATA_URL`：`静态快照`
- REST health 成功：`行情服务在线`
- REST health、CORS 或 payload 校验失败：`静态快照 · 行情服务状态未知`

第三种状态明确表示 health 未验证成功，不推断整个行情服务或 WebSocket 已宕机。

这次不重做布局、不替换 ECharts，也不批量把现有按钮改造成新组件。

## Explicitly deferred

### pnpm workspace migration

迁移 npm 到 pnpm 需要重新生成并验证 `pnpm-lock.yaml`，同时修改 GitHub Actions cache/install/audit 命令。当前 GitHub Connector 环境没有私库 checkout，也不能访问 npm registry，因此不能可靠生成和执行 pnpm lockfile。伪造 lockfile 会让 PR 表面现代、实际不可复现，因此拆到后续独立 PR。

### shadcn/ui migration

shadcn/ui 需要先完成包管理器和 Tailwind/shadcn 依赖的可验证安装。后续 PR 应只建立组件基础设施和迁移少量高复用控件，不做视觉重写；ECharts 继续负责图表。

### Dynamic research API and PostgreSQL

本 PR 不把静态研究 snapshot 改为在线 FastAPI endpoint，也不引入 PostgreSQL。研究 API 需要先确定后端部署位置和交互需求；PostgreSQL 等到 watchlist、saved research runs、annotations 等持久业务状态出现后再引入。

## Data flow after this PR

```text
Static research/dashboard data
Python generators -> data.json / research snapshots -> React

Live market overlay
React -> REST /healthz (service status)
       -> explicit CORS allowlist when cross-origin
React -> REST /v1/quotes/{symbol} (typed client available)
React -> WebSocket /v1/stream (existing live overlay)

FastAPI -> typed Pydantic responses -> OpenAPI
                                      -> future TS codegen
```

## Error handling

- REST client 的网络错误、CORS 错误和 payload 校验错误只把 health 状态设为 unknown，不阻断 Dashboard 静态数据，也不推断 WebSocket 状态。
- quote 404/400 继续由 FastAPI 返回标准错误；client 调用者得到带 HTTP status 的错误。
- 未配置 CORS allowlist 时保持默认关闭跨 origin REST 访问，不隐式开放任意网页。
- WebSocket 的现有 stale/reconnect 行为保持不变。

## Testing

Python：

```bash
cd apps/market-data-service
uv run --locked pytest -q
uv run --locked ruff check src tests scripts
```

Frontend：

```bash
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
```

完整验证：

```bash
uv run --locked --extra dev pytest -q
uv run --locked python scripts/check_foundation.py
```

## Rollback

所有生产行为都保留静态 Dashboard 作为降级路径。回滚本 PR 只需要撤销 response model、CORS allowlist、REST client/status UI 和文档，不涉及数据迁移、数据库 schema 或部署状态。
