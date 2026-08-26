# 项目维护加固实施计划

> Agent 执行提示：本计划记录 2026-08-26 维护 PR 的最终范围。实现过程中发现的新事实已经回填，避免让最初假设和最终代码长期分叉。

目标：修复已确认的 Dashboard 正确性问题，补齐质量检查、部署验收和图表图片导出，并把主要说明文档统一为准确、自然的中文。

架构：保持当前 monorepo 边界，不提前导入 Niu Men，也不在本 PR 进行 R-Breaker 数据层大重构或三个大型 Python 模块的全面拆分。行为修复先补回归测试，前端图片复用现有 React 与 ECharts，通过 Playwright 截图，自动化继续使用手动 GitHub Actions。

技术栈：Python 3.11+、uv、pytest、pytest-cov、Ruff、pip-audit、React、TypeScript、Vite、Node.js 22、npm、Playwright、Cloudflare Workers、GitHub Actions。

设计依据：`docs/superpowers/specs/2026-08-26-a-share-trading-research-monorepo-design.md`

## 全局约束

- 保持 `niu_men.research_snapshot.v2` 线协议兼容。
- 不把 `research-workspace`、`market-data-platform` 或 `etf-minute-fetcher` 源码导入本仓库。
- 不提交原始行情、完整 OOS CSV、凭据、本机数据目录或图表导出产物。
- 允许提交经过审查和校验的 `web/public/data.json` 与可选 `research.json` 作为发布基线，这类 release input 与原始行情缓存职责不同。
- GitHub Actions 继续只允许手动触发。
- 中文文档优先使用中文标点，代码、命令、路径、产品名和协议名保持原样。
- 本 PR 不重构 R-Breaker 的内部数据下载层。
- 本 PR 不进入 M2/M3 的共享 package 和整体依赖重构。

---

## Task 1：让 M1 文档边界可继续演进

涉及：

```text
scripts/check_foundation.py
tests/test_foundation.py
```

问题：M1 checker 原本只允许几个写死日期的 superpowers 文件，新建正常设计或计划文档也会被判为越界。

实施：

- 为 `docs/superpowers/plans/` 和 `docs/superpowers/specs/` 增加受控目录前缀。
- 合并后续发布基线规则，只允许精确的 `web/public/data.json` 和 `web/public/research.json`，继续拒绝其他任意 `web/public/*`。
- 允许 `apps/dashboard/web/scripts/` 维护图表导出代码。
- 继续拒绝 Niu Men 提前导入、`data/raw`、artifact、凭据和 gitlink。
- 增加临时 Git 仓库回归测试，确认新设计文档、受控快照和图表脚本边界。

验证目标：

```bash
uv run --locked --extra dev pytest -q tests/test_foundation.py
uv run --locked python scripts/check_foundation.py
```

## Task 2：修复交易风格和 VWAP 数据语义

涉及：

```text
apps/dashboard/src/trading_research/dashboard/astock_tech.py
apps/dashboard/tests/test_default_instrument.py
apps/dashboard/tests/test_etf_dashboard_integration.py
```

发现：

1. `determine_trading_style()` 返回英文风格名称，后续参数逻辑却匹配中文子串，导致自动系数分支无法按预期命中。
2. `roll_ratio` 只被计算和覆盖，没有进入 Dashboard 输出或任何执行逻辑，属于无消费者 dead code。
3. 缺少分时数据时 `vwapDev` 被写成 `0`，会把未知误表示为恰好没有偏离。

实施：

- 增加 `vwap_deviation_factor_for_style(style)` 显式映射。
- `Mean reversion + VWAP` 使用 `0.4`。
- `Trend-following + Breakout` 使用 `0.6`。
- 其他当前风格使用 `0.5`。
- 保留单证券 `vwap_dev_k` 覆盖。
- 删除未使用的 `roll_ratio` 配置和运行计算。
- 缺少分时数据时 `vwapDev = null`，ATR 派生的 `vwapDevThreshold` 仍可输出。

## Task 3：让分时缓存绑定交易日

涉及：

```text
apps/dashboard/src/trading_research/data/data_sources.py
apps/dashboard/tests/test_data_sources.py
apps/dashboard/tests/test_etf_data_sources.py
```

问题：旧分时缓存路径为 `data/raw/intraday/<code>.csv`，没有交易日期。历史请求实时源失败时，可能读取另一交易日缓存，再由上层拼成请求日期。

实施后的路径：

```text
data/raw/intraday/<code>/<YYYYMMDD>.csv
```

旧的无日期分时缓存不再作为历史请求兜底。daily 和 calendar 缓存结构保持不变。

## Task 4：移除 Dashboard import 副作用

涉及：

```text
apps/dashboard/src/trading_research/dashboard/astock_tech.py
apps/dashboard/tests/test_cli.py
```

问题：只 import 模块就会：

- 全局 `warnings.filterwarnings('ignore')`
- 修改进程级 socket 默认 timeout
- 打印 AKShare 和 pandas 版本

实施：

- 删除全局 warning 屏蔽。
- socket timeout 只在真正运行 `main()` 时设置。
- 版本输出只在主流程运行时打印。
- 子进程测试验证纯 import 不产生 stdout，也不改变已有 socket timeout。

## Task 5：修复部署链和部署后检查

涉及：

```text
.github/workflows/deploy-dashboard.yml
apps/dashboard/scripts/validate_static_assets.py
apps/dashboard/scripts/check_deployment.py
apps/dashboard/tests/test_static_assets.py
apps/dashboard/tests/test_check_deployment.py
apps/dashboard/web/public/data.json
apps/dashboard/web/public/research.json
apps/dashboard/web/src/api.ts
```

演进过程：

1. 最初审计发现干净 checkout 构建 React 时没有可靠 `data.json`，一度考虑在 GitHub runner 现场抓行情。
2. 并行 PR #6 随后采用更稳定方案：把经过审查的静态行情和研究快照作为发布基线提交，并在部署前运行独立 validator。
3. 这个方案更符合当前环境，因为 GitHub runner 访问国内行情源、凭据和配额都不够稳定，部署结果不应取决于一次即时抓取是否成功。
4. 旧部署 smoke check 同时把产品语义上可选的 `research.json` 当成必需文件，需要修正。

最终实施：

- 保留并合并 PR #6 的 `data.json`、`research.json`、`validate_static_assets.py`、静态资产测试和 `api.ts` content-type 检查。
- `Deploy Dashboard` 先安装锁定前端依赖，再校验仓库中的发布基线。
- `data.json` 缺失、损坏、`generatedAt` 无效或 `stocks` 为空时阻止部署。
- 前端单元测试和生产构建通过后才进入 Workers 部署。
- `CLOUDFLARE_PUBLIC_URL` 存在时运行部署后检查。
- smoke check 要求首页和非空 `data.json`。
- `research.json` 404 或 SPA fallback HTML 视为研究快照未发布。
- `research.json` 真正返回 JSON 时才检查 v1/v2 schema。
- 运行时 `data/raw/` 继续留在 Git 之外，受控静态快照不视为原始行情缓存。

## Task 6：补齐手动质量门槛

涉及：

```text
apps/dashboard/pyproject.toml
.github/workflows/foundation.yml
```

实施：

- Dashboard coverage 从 `--cov=./` 收敛到 `trading_research`。
- 开启 branch coverage。
- 修正 package Homepage，不再使用 `example.invalid`。
- Ruff 采用现代 `[tool.ruff.lint]` 配置。
- 手动 foundation workflow 增加：
  - root 与 Dashboard lockfile 检查
  - Ruff 基础错误检查
  - 根级 pytest
  - Dashboard pytest 与 coverage
  - Python 依赖审计
  - `npm ci`
  - 前端单元测试
  - TypeScript/Vite 生产构建
  - `npm audit --audit-level=high`
  - foundation boundary check
  - whitespace 检查

Ruff 本轮先把稳定的基础错误类别作为 CI 门槛。更激进的 complexity、annotation、docstring 和安全规则在看到真实基线后分阶段提高，避免通过大量 ignore 人为制造绿色。

## Task 7：增加 PNG 图表导出

新增：

```text
apps/dashboard/web/scripts/export-charts.mjs
apps/dashboard/web/scripts/export-charts.test.mjs
```

修改：

```text
apps/dashboard/web/package.json
.gitignore
apps/dashboard/README.md
apps/dashboard/docs/outputs.md
apps/dashboard/docs/web-frontend.md
apps/dashboard/docs/troubleshooting.md
```

设计：直接用 Playwright 截取 React 和 ECharts 已渲染组件，不再实现第二套 Python 图表。

命令：

```bash
cd apps/dashboard/web
npm run export:charts
```

本地模式自动启动已有 `dist` 的 Vite preview。远程模式：

```bash
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --output /var/lib/trading-research/charts \
  --theme light
```

导出：

```text
overview-<date>.png
<code>-workspace-<date>.png
<code>-daily-<date>.png
<code>-intraday-<date>.png
manifest.json
```

manifest schema：

```text
trading_research.chart_export.v1
```

支持环境变量：

```text
DASHBOARD_EXPORT_URL
DASHBOARD_EXPORT_DIR
DASHBOARD_EXPORT_THEME
```

默认输出 `artifacts/charts/<generatedAt>/`，该目录不进入 Git。脚本要求 `data.json.stocks` 非空，并为 K 线和分时图使用明确的单节点 locator，避免 Playwright strict-mode 歧义。这个稳定输出适合 Hermes Agent、cron、邮件机器人或其他消息推送工具消费。

## Task 8：中文化并校准说明文档

范围：

```text
README.md
AGENTS.md
docs/migration/**
docs/superpowers/specs/**
docs/superpowers/plans/**
packages/*/README.md
apps/dashboard/README.md
apps/dashboard/docs/**
```

原则：

- 中文为主，保留必要技术英文和代码标识符。
- 中文正文使用中文标点。
- 减少翻译腔、重复否定铺垫和无意义强调。
- 历史迁移文档保留当时命令、SHA 和测试数字，不把历史证据篡改成最新结果。
- 当前操作文档以现行代码和 workflow 为事实来源。
- 明确当前仓库没有 Git submodule。
- 明确 Dashboard 已由 monorepo 维护，Niu Men 仍是外部 producer。
- 记录 M1 首次排除生成快照与后续受控发布基线之间的时间线，避免把两种不同阶段的规则混为一谈。

## Task 9：完整验证和 PR 审查

完整环境需要运行：

```bash
uv lock --check
uv lock --project apps/dashboard --check
uv run --locked --extra dev pytest -q
uv run --project apps/dashboard --locked pytest -q apps/dashboard/tests
uv run --locked python scripts/check_foundation.py
npm ci --prefix apps/dashboard/web
npm test --prefix apps/dashboard/web
npm run build --prefix apps/dashboard/web
npm audit --prefix apps/dashboard/web --audit-level=high
```

图片导出浏览器验收需要：

```bash
cd apps/dashboard/web
npx playwright install chromium
npm run build
npm run export:charts
```

本次会话中的仓库写入全部通过官方 GitHub connector 完成。当前可用执行环境不包含项目完整 Python 和 Playwright 浏览器依赖，因此不能把未实际执行的全量测试标记为已通过。PR 需要明确列出已做的静态验证，并由仓库手动 `Monorepo foundation` workflow 完成完整依赖环境验证。

## 后续验证结果

以上内容记录了 PR 初始阶段的执行限制。PR #7 后续在本地完整环境中完成了依赖解析和验证，并于 2026 年 8 月 26 日合并到 `main`，合并提交为 `7bd3740`。

后续验证结果如下：

- 根级测试 26 个通过。
- Dashboard 测试 48 个通过，覆盖率为 53%。
- Ruff、foundation 检查、前端 29 个单元测试和 Vite 构建通过。
- `npm audit --audit-level=high` 未发现漏洞。
- `pip-audit` 未发现已知漏洞。
- PNG 图表已从线上 Worker 成功导出。

依赖升级只修改了 `apps/dashboard/uv.lock`，包括 `aiohttp`、`fonttools`、`idna`、`lxml`、`pillow`、`pygments`、`pytest`、`requests`、`soupsieve` 和 `urllib3`。当前日常检查应以合并后的 workflow 和文档为准。

## 明确留给后续 PR 的工作

- R-Breaker 复用统一 `data_sources`，删除第二套行情下载和缓存逻辑。
- 确认外部调用方后删除 `apps/dashboard/backtest/rbreaker.py` 兼容壳。
- 评估删除或上移 `apps/dashboard/scripts/flow.ps1`。
- 按职责拆分 `astock_tech.py`、`data_sources.py`、`rbreaker.py`。
- M1 Niu Men 历史导入。
- M2 `research-core` 契约抽取。
- M3 Python package 和依赖收敛。
- 根据真实 Ruff、类型检查和 coverage 基线逐步提高门槛。
