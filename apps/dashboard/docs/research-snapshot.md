# 牛门线研究快照接入

Dashboard 保留原有 `web/public/data.json` 作为盘前与日内数据源，并通过策略注册表读取不同策略的静态研究快照。牛门线当前使用 `web/public/research.json`，未来 R-Breaker 使用 `web/public/rbreaker-research.json`。

## 数据边界

- `data.json` 仍由 `astock_tech.py` 生成，负责最新价格、ATR、VWAP、ORB、K 线和分时图。
- `research.json` 必须由 `niu-men-line-strategy` 的研究快照导出器生成，Dashboard 不重新计算 NML、行业上下文、滚动样本外或涨跌停成交约束。
- 迁移期同时支持 `niu_men.research_snapshot.v1` 和 `niu_men.research_snapshot.v2`。

这样可以让前端继续作为纯静态站点，不需要增加后端接口，也不需要把两个仓库做成 submodule。原始 Niu Men v1/v2 JSON 由 adapter 转换成通用 `StrategySnapshot` 后才交给研究 UI。

## 契约资产

Niu Men 是当前研究快照 schema 的规范来源。契约资产由 Niu Men 发布 workflow 通过 reviewable PR 同步到 Dashboard：

```text
niu-men-line-strategy/schemas/research-snapshot.schema.json
  -> wu-t0-trading-dashboard/schemas/research-snapshot.schema.json

niu-men-line-strategy/tests/fixtures/research_snapshot/*.json
  -> wu-t0-trading-dashboard/tests/fixtures/research_snapshot/*.json
```

Dashboard Web CI 使用复制后的 JSON Schema 验证 fixture 和 `web/public/research.json`，并继续使用现有 parser 和 Niu Men adapter 转换为通用 `StrategySnapshot`。Dashboard 不重新计算 OOS，不猜测 provenance，也不 import Niu Men 的 Python 内部模块。

研究快照是可选输入。契约资产或发布 PR 被拒绝时，Dashboard 继续使用上一次成功的 `research.json`，没有可用快照时只在策略研究区域显示缺失状态，盘前与日内行情不受阻塞。

在完成至少一个稳定发布周期前，原 Dashboard 仓库和 Niu Men 仓库都保持活动状态。后续 monorepo 迁移会保留两边 Git 历史和回滚能力，不会直接删除原项目。

## 生成与放置

在 `niu-men-line-strategy` 中运行现有导出器，或使用发布命令：

```bash
uv run python scripts/export_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output ../wu-t0-trading-dashboard/web/public/research.json
```

发布流水线使用以下稳定入口：

```bash
uv run python scripts/publish_dashboard_snapshot.py \
  --oos-json /path/to/niu_men_industry_context_oos_full_market_expanded_20260825.json \
  --research-manifest artifacts/etf-industry-context-20260825/manifest.json \
  --output web/public/research.json
```

该命令只负责把已经生成的 OOS 产物转换为 `research_snapshot.v2`，不运行策略、不猜测 provenance，也不会把本机绝对路径写入快照。跨仓库发布 workflow 会用它生成文件，然后对 Dashboard 打开 PR，不直接修改 Dashboard `main`。

然后正常构建 Dashboard：

```bash
cd web
npm run build
```

Vite 会像处理 `data.json` 一样把 `research.json` 原样复制到 `web/dist/`，Cloudflare Workers Static Assets 无需增加运行时服务。

## 缺少或损坏快照时

`research.json` 是可选输入。文件不存在，或者静态托管把缺失资源回退成 HTML 时，盘前与日内区域继续正常工作，策略研究区域显示尚未部署快照的提示。这样行情更新不会被研究产物缺失阻断。

文件存在时，前端会先检查支持的 schema 版本和研究区域实际使用的关键结构。未知版本、v2 来源结构缺失或关键字段类型错误时，只在策略研究区域显示加载错误，盘前与日内区域继续使用 `data.json`。

## 新鲜度判断

研究新鲜度只比较两个数据日期：

- `data.json.generatedAt` 是当前盘前与日内行情数据日期。
- `research.json.source.dataDate` 是研究结果实际使用的数据截止日。

研究日期早于行情日期时，研究区域明确显示研究快照已过期，并同时列出两个日期。研究日期等于或晚于行情日期时显示研究数据与行情同步。日期格式无法可靠判断时显示研究新鲜度未知。

v2 快照若明确设置 `quality.checks.provenanceComplete=false`，即使 `source.dataDate` 看起来是合法日期，前端也显示研究新鲜度未知。这样不会用一个来源链不完整的日期制造同步结论。

这个判断不使用浏览器当前日期。周末、节假日和夜间打开页面不会因为时间流逝本身产生假过期警告。

## v2 来源信息

v2 额外展示：

- `source.researchCommit` 对应研究 OOS 运行时记录的 `niu-men-line-strategy` commit。
- `source.oosGeneratedAt` 对应 OOS 研究运行日期。
- `source.dataPlatformManifest.schemaVersion` 对应数据平台 manifest 契约版本。
- `source.dataPlatformManifest.generatedAt` 对应数据平台 manifest 生成时间。
- 顶层 `generatedAt` 对应 `research.json` 的实际导出时间。

历史 v1 快照没有这些 provenance 字段时仍然可以展示研究内容，来源详情会明确标注历史 v1 未提供，不会猜测 commit 或 manifest 版本。

## 展示内容

牛门线策略页展示：

- 请求、评估和跳过标的覆盖
- 行业 ETF 映射置信度和覆盖率
- 行业上下文 warmup 跳过情况
- 六个固定策略变体的 OOS 年化收益、Sharpe、最大回撤和交易次数中位数
- 涨停阻止买入和跌停阻止卖出日计数
- 按 `foldId` 的滚动窗口年化收益中位数
- 快照内置的数据质量检查
- 研究数据新鲜度和 v2 来源追踪信息

策略对比页只接受已经成功解析且质量状态可展示的策略快照。当前只有牛门线快照时，对比页会显示“需要第二个已发布快照”；R-Breaker 研究发布后无需改动通用表格组件即可接入。

当前 `foldId` 是每只股票内部的滚动窗口序号，不保证不同股票的同一编号对应同一自然日区间。图表因此表示第 N 个样本外窗口的横截面摘要，不应解释为统一日历时间序列。
