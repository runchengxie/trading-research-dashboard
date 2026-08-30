# Dashboard Research Publication and Contracts Design

## Goal

让 Dashboard 的研究代码、静态数据和线上 Worker 形成可验证的发布闭环，并让滚动研究结果、R-Breaker 结果和 ICT 衍生上下文以真实且不误导的方式展示。

## Scope

本设计拆成两个独立 PR：

1. 发布闭环与展示语义：数据刷新、contextual enrichment、R-Breaker 快照发布、部署触发、VWAP/ORB 展示和缺失状态文案。
2. 研究数据契约：滚动窗口真实日期、R-Breaker 多窗口汇总，以及 A 股涨跌停约束指标的语义化输出。

不在本次范围内：浏览器端直连 yfinance/Alpaca、提交原始行情或本机缓存、伪造 R-Breaker 未建模的涨跌停统计、把 ICT 叙事转换成主观评分。

## Current Evidence

- 线上 `data.json` 的宝莱特没有 intraday bars，且缺少顶层 `contextualResearch`。
- 线上 `rbreaker-research.json` 是旧版快照，缺少 `walkForward`，`sharpeMedian` 为 `null`。
- Dashboard #62 的 contextual research 代码已进入仓库，但 enrichment 仍是手动的第二步。
- `research.json` 的 fold 目前只有 ordinal；前端已经支持日期字段，但生产数据没有提供日期。
- R-Breaker 生成器当前是单次输入 artifact 的单样本摘要，不是多窗口 OOS 生成器。

## Design

### PR 1：发布闭环与展示语义

#### Data flow

权威发布流程按以下顺序执行：

```text
market-data refresh
  -> validate candidate data.json
  -> enrich_contextual_research
  -> generate/validate R-Breaker snapshot
  -> frontend tests and build
  -> deploy Worker
  -> download and validate deployed assets
```

`contextualResearch` 必须在候选 `data.json` 验证通过后生成，并随同候选文件进入构建目录。若 enrichment 失败，发布流程失败，不静默发布没有上下文的旧格式数据。

普通 `main` 合并继续只做验证，不未经明确的 authoritative 条件覆盖线上。由于仓库 Actions 配额有限，不恢复 `push`、`pull_request` 或定时自动部署；增加一个可审计的手动 authoritative 发布入口，并让它复用同一套生成和检查步骤。

#### Frontend

- 保留上一交易日分时的空状态；当 payload 没有 bars 时明确显示“暂无可用分时数据”。
- 将 VWAP、ORB 上轨和 ORB 下轨提升到主要模型读数区域，同时保留高级指标表作为完整明细。
- Contextual research panel 继续由顶层 `contextualResearch` 驱动；缺失时显示数据未发布提示，而不是空白区域。
- 策略比较中区分三种状态：有数值、该策略没有该指标、两个策略没有共同 variant。避免用同一个 `—` 掩盖不同原因。

#### R-Breaker in PR 1

发布当前已实现的 R-Breaker 快照，确保日期、年化收益和 Sharpe 能在线展示。`profitFactorMedian`、涨停阻止买入和跌停阻止卖出日若生产端没有计算，统一展示“未提供/未建模”，不得填充 0。

### PR 2：研究数据契约

#### Rolling summaries

每个 rolling summary 必须携带真实的 `startDate` 和 `endDate`，格式为 ISO 日期 `YYYY-MM-DD`。`foldId` 仍保留用于稳定排序和识别，但不再作为时间展示的替代值。

当多标的交易日历不同，生产端必须明确汇总日期语义：日期字段表示该 fold 实际纳入样本的整体 OOS 日期范围；如需要保留逐标的精确日期，另加 per-symbol 日期信息，不用一个虚构日期替代。

#### R-Breaker rolling research

将 R-Breaker 的单次 artifact 摘要与真正 rolling OOS 分开建模。rolling 生成器接收明确的训练长度、测试长度、步长和日期范围，输出多个 fold，并对每个 fold 记录：

- `foldId`
- `startDate`
- `endDate`
- annualized return
- Sharpe
- max drawdown
- trade count
- win rate
- profit factor（无法计算时为 null）

只有在生成器实际执行多个 OOS fold 后，前端才展示“滚动窗口年化收益中位数”等 rolling 图表。

#### A-share execution constraints

涨停阻止买入和跌停阻止卖出必须来自实际交易模拟的逐日计数。若 R-Breaker 输入数据或执行模型没有涨跌停字段和订单阻断逻辑，快照明确标记 capability 为 `not_modelled`，前端显示“未建模”，不与真实的 0 天混淆。

## Error handling

- 静态资产校验拒绝缺少必要字段、非法日期或不一致 schema。
- authoritative 发布前必须检查 contextual enrichment 的 coverage 和 R-Breaker snapshot 的结构。
- 部署后重新读取线上 JSON，确认宝莱特 intraday、`contextualResearch`、R-Breaker `walkForward` 与 Sharpe 的实际状态。
- 任一检查失败都保留线上旧版本，不把不完整候选发布出去。

## Testing

PR 1 至少覆盖：

- enrichment 被发布流程调用并产生顶层 `contextualResearch`；
- 最新数据包含有分时的标的时，分时组件渲染图表；
- VWAP/ORB 主指标显示数值或明确空状态；
- 策略比较正确区分未提供指标和无共同 variant；
- workflow YAML、静态资产校验、前端测试和 build。

PR 2 至少覆盖：

- rolling summary 缺少日期时生产端测试失败；
- 日期存在时前端横坐标使用真实日期；
- R-Breaker 多 fold 生成并正确计算中位数；
- `not_modelled` 与真实 0 的展示不同；
- 单样本旧快照仍能兼容读取，但不冒充 rolling research。

## Rollback

每个 PR 都只修改生成器、workflow、静态契约和前端兼容逻辑，不删除旧版读取路径。若线上验证失败，停止部署并保留上一版 Worker；若 PR 需要回滚，恢复 workflow 和静态资产提交即可，不涉及原始行情删除。
