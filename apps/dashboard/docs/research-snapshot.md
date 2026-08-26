# 研究快照接入

Dashboard 使用两类静态数据：

```text
web/public/data.json       行情、指标、K 线和分时数据
web/public/research.json   可选的策略研究快照
```

当前仓库提交了一份经过验证的 `data.json` 发布基线，也可以提交经过审查的 `research.json`。研究计算仍由独立仓库 `niu-men-line-strategy` 负责，Dashboard 只负责契约校验、适配和展示。

## 当前仓库边界

当前 monorepo 尚未导入 Niu Men 源码：

```text
packages/niu-men-line-strategy/   目标位置，源码尚未导入
packages/research-core/           共享契约目标位置，M2 尚未抽取
apps/dashboard/                   当前研究快照 consumer
```

当前仓库没有使用 Git submodule。Niu Men 与 Dashboard 通过版本化 JSON 契约连接。

Dashboard 保留 consumer 侧契约资产：

```text
apps/dashboard/schemas/research-snapshot.schema.json
apps/dashboard/tests/fixtures/research_snapshot/
```

在 M2 共享契约抽取完成前，Niu Men 仍是研究快照 schema 的规范来源。共享 schema、fixture 和 provenance 规则后续计划迁移到 `packages/research-core/`，线协议继续保持兼容。

## 支持版本

迁移期支持：

```text
niu_men.research_snapshot.v1
niu_men.research_snapshot.v2
```

原始 Niu Men JSON 先经过 parser 和 adapter，转换成前端通用 `StrategySnapshot`。研究 UI 不直接依赖策略内部 Python 模块。

## 数据职责

`data.json` 负责：

- 最新行情日期
- 日线和分时序列
- ATR、VWAP、ORB
- 支撑阻力和关键价格
- Dashboard 交易风格

`research.json` 负责 Niu Men 研究结果，例如：

- 请求、评估和跳过证券覆盖
- 行业 ETF 映射质量
- 滚动样本外结果
- 策略变体指标
- 涨跌停成交约束统计
- provenance 和质量检查

Dashboard 不重新计算 NML、OOS、行业上下文或 provenance。

## 从 Niu Men 生成快照

Niu Men 独立仓库当前保留：

```text
scripts/export_dashboard_snapshot.py
scripts/publish_dashboard_snapshot.py
```

生成 `research_snapshot.v2` 时可以在 Niu Men 仓库执行发布脚本，并把输出指向当前 monorepo：

```bash
uv run python scripts/publish_dashboard_snapshot.py \
  --oos-json /path/to/oos-result.json \
  --research-manifest /path/to/research-manifest.json \
  --output /path/to/a-share-trading-research/apps/dashboard/web/public/research.json
```

脚本只应把已经完成的研究产物转换成版本化快照，不在发布步骤重新运行策略，也不把本机绝对路径写入 provenance。

Niu Men 还保留 `publish-dashboard-snapshot.yml` 历史发布 workflow。当前 monorepo 已经接管 Dashboard 代码和部署，因此跨仓库自动发布流程重新启用前需要单独审查目标仓库、分支和路径，不能默认继续写入旧 Dashboard 仓库。

## 提交与部署

当前生产部署使用仓库中已经审查的静态快照。更新研究基线时推荐流程：

1. 在 Niu Men 数据和研究环境生成新的 `research.json`。
2. 写入 `apps/dashboard/web/public/research.json`。
3. 运行 `python apps/dashboard/scripts/validate_static_assets.py`。
4. 运行前端单元测试和生产构建。
5. 通过 PR 审查快照和代码变化。
6. 手动触发 Dashboard 部署 workflow。

`Deploy Dashboard` 不在 GitHub runner 上重新运行 Niu Men 研究，也不现场抓取行情。它验证当前 commit 中的静态发布基线，然后测试、构建和部署。

## 缺少研究快照

研究快照在产品语义上仍是可选输入。即使当前仓库提交了一份研究发布基线，前端也必须正确处理以下情况：

- `research.json` 不存在
- Workers SPA fallback 对缺失路径返回 HTML
- 快照 schema 不受支持
- v2 provenance 或关键字段不完整

这些情况只影响策略研究区，盘前概览和日内工作台继续读取必需的 `data.json`。

部署后 smoke check 也遵循这个边界：`data.json` 必须存在并包含证券数据，`research.json` 只有在实际返回 JSON 时才校验 schema。

## 新鲜度判断

研究新鲜度比较：

```text
data.json.generatedAt
research.json.source.dataDate
```

研究日期早于行情日期时，研究区显示快照已过期，并展示两个日期。研究日期等于或晚于行情日期时显示同步。

日期无法可靠解析时显示新鲜度未知。

v2 快照若设置：

```text
quality.checks.provenanceComplete = false
```

即使 `source.dataDate` 看起来合法，也按来源链不完整处理，不用该日期制造同步结论。

判断不使用浏览器当前日期，因此周末、节假日或夜间打开页面不会因为自然时间流逝产生假过期状态。

## v2 provenance

v2 可以展示：

- `source.researchCommit`
- `source.oosGeneratedAt`
- `source.dataPlatformManifest.schemaVersion`
- `source.dataPlatformManifest.generatedAt`
- 顶层 `generatedAt`

历史 v1 没有这些字段时仍可以展示研究内容，来源详情明确标记缺失，不猜测 commit 或 manifest。

## 策略研究展示

当前牛门线页面可以展示：

- 证券覆盖和跳过情况
- 行业 ETF 映射置信度与覆盖率
- 行业上下文 warmup 情况
- 固定策略变体的 OOS 年化收益、Sharpe、最大回撤和交易次数中位数
- 涨停阻止买入、跌停阻止卖出日计数
- 按 `foldId` 汇总的滚动窗口结果
- 快照质量检查
- 研究新鲜度和来源信息

策略对比只有在至少两个策略都成功加载且质量状态允许展示时才显示共同指标。

`foldId` 是单只证券内部的滚动窗口编号，不保证不同证券的相同编号对应同一自然日期区间。因此按 `foldId` 的图表表示第 N 个样本外窗口的横截面摘要，不能解释成统一日历时间序列。

## 与图片导出的关系

当前 `npm run export:charts` 导出盘前概览和日内工作台图表，不导出策略研究页面。图片自动化只依赖必需的 `data.json`，不会因为研究快照缺失而阻塞每日行情推送。
