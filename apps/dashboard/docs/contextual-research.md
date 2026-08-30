# Contextual Research

Contextual Research 是 Dashboard 的策略无关研究层。它把现有行情快照中的可观察事实整理为更高时间框架背景、参考价位、session、day archetype、setup event、跨标的确认和事件研究，供日内工作台展示和后续条件化统计使用。

它刻意不定义“机构意图”“聪明钱行为”或任何主观综合评分。所有 detector 都必须能由输入数据和明确规则复现。

更重要的一条约束是 **point-in-time safety**：用于历史 setup 触发的输入，必须在事件发生时已经可知。完整交易日结束后才能知道的值可以用于事后描述和 outcome，但不能冒充事前信号。

## 生成流程

先按原有方式生成 `data.json`：

```bash
cd apps/dashboard
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --json web/public/data.json
```

再原子注入 contextual research：

```bash
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json
```

也可以写到另一个文件：

```bash
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json \
  --output /tmp/data-with-context.json
```

`contextualResearch` 是 optional。没有运行 enrichment 的旧快照仍可由 Dashboard 正常加载。

### 跨日条件统计

保留多个已经生成的 Dashboard/contextual snapshot 后，可以在发布时生成可选的
`data.json.conditionalResearch`。历史输入必须是 Dashboard JSON 对象、contextual snapshot
对象，或这些对象组成的 JSON 数组；`--history` 可以重复传入：

```bash
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json \
  --history /path/to/contextual-2026-08-28.json \
  --history /path/to/contextual-2026-08-29.json
```

策略条件统计需要另行提供标准化 outcome 数组，不会从策略总览指标反推：

```json
[
  {
    "strategyId": "r-breaker",
    "variantId": "default",
    "instrument": "TSLA.US",
    "dataDate": "2026-08-29",
    "session": "morning",
    "return": 0.012,
    "mfe": 0.018,
    "mae": -0.006,
    "win": true
  }
]
```

```bash
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json \
  --history /path/to/contextual-history.json \
  --strategy-outcomes /path/to/strategy-outcomes.json
```

`conditionalResearch` 按 instrument、market、session、day archetype、setup event、reference
level 以及可选 strategy/variant 分组，输出 sample count、win rate、expectancy、mean return、
MFE/MAE、日期数和标的数。缺失历史或 outcome 时保持可选/空覆盖，不制造统计结果。

如果只有最新 `data.json`，可以先用其中的日线历史和配置好的 A 股分时 provider 重建历史
contextual snapshots，再交给上面的 enrichment：

```bash
uv run python -m trading_research.scripts.build_contextual_history \
  --input web/public/data.json \
  --output /path/to/contextual-history.json \
  --sessions 20 \
  --codes sz300246

uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json \
  --history /path/to/contextual-history.json
```

该工具只使用研究日期之前的日线来派生 PDH/PDL 和 ATR，并把历史分时时间补成完整日期；
它不会把当前日的最终指标回填到过去。历史 provider 无法返回某个交易日时，命令会失败，
不会静默生成不完整的条件统计。提交或发布前仍需运行严格静态校验。

在 authoritative 发布中，enrichment 不是可选步骤。必须先完成行情候选生成，再运行 enrichment 和严格校验；定时 runtime report 仍默认使用 shadow 模式，不覆盖线上 Worker。

完整发布顺序是：

1. 生成最新 `data.json`，包括宝莱特的可用分时数据。
2. 运行 `enrich_contextual_research`，写入顶层 `contextualResearch`。
3. 使用 `validate_static_assets.py --require-contextual` 校验 coverage。
4. 生成并校验 R-Breaker snapshot。
5. 运行前端测试和生产构建。
6. 在 authoritative 条件下部署 Worker，并重新读取线上 JSON 做 smoke check。

## Contract

Canonical schemas 位于 `packages/research-core/src/research_core/schemas/`：

- `trading_research.market_context.v1`
- `trading_research.setup_event.v1`
- `trading_research.event_study.v1`
- `trading_research.contextual_snapshot.v1`
- `trading_research.conditional_research.v1`

单日观察快照写入 `data.json.contextualResearch`；跨日汇总写入可选的
`data.json.conditionalResearch`。现有 `stocks`、`research.json`、`rbreaker-research.json` 和
`trading_research.strategy_snapshot.v1` 不变。

## Point-in-time Reference Levels

Context 层可以展示这些语义化价位：

- `previous_day_high`
- `previous_day_low`
- `previous_5d_high`
- `previous_5d_low`
- `opening_range_high`
- `opening_range_low`
- `vwap`
- `support`
- `resistance`
- `key`
- `center`

其中 `previous_day_*` 和 `previous_5d_*` 不读取静态快照中面向“当前生成日”的 `yesterdayHigh/yesterdayLow` 指标，而是根据 **分时研究日期之前** 的 daily rows 重新派生。这样不会把研究当天完整形成的 high/low 错当成当天开盘前已经知道的 PDH/PDL。

每个 level 都包含价格、来源标签，以及相对当前价的 `distancePct`。当前价优先取分时最后一个价格，没有分时时回退到 `lastClose`。

`VWAP（日终上下文）`、通用 support/resistance/key/center 可以作为已完成交易日的描述，但当前 `setup-detector.v1` 不使用它们进行历史触发检测，因为现有静态快照没有 point-in-time VWAP 或这些通用 level 的历史版本。

## Higher-Timeframe Context

`market_context.v1.higherTimeframe` 使用研究日期之前的最近 20 根 daily bars：

- `trend20`: `up` / `down` / `flat` / `insufficient_data`
- `return20`: 20-bar close-to-close return
- `rangePosition20`: 最新 prior close 在 20-bar high/low 区间中的位置，范围 0–1

首版把 `return20 > 2%` 标为 `up`，`return20 < -2%` 标为 `down`，其余标为 `flat`。这只是一个透明、可替换的研究分箱，不被宣传成真实“市场方向”。

当前交易日的 daily bar 不参与这个 20-bar 背景，避免把收盘后的信息泄漏到当日 setup context。

## Session Model

Session 使用行情快照中已经本地化到标的时区的 wall-clock timestamp。当前默认窗口：

### US

| Session | 本地时间 |
| --- | --- |
| `premarket` | 04:00–09:30 |
| `opening_range` | 09:30–10:30 |
| `morning` | 10:30–12:00 |
| `midday` | 12:00–13:30 |
| `afternoon` | 13:30–15:00 |
| `power_hour` | 15:00–16:00 |

### CN

| Session | 本地时间 |
| --- | --- |
| `open` | 09:30–10:00 |
| `morning` | 10:00–11:30 |
| `afternoon_open` | 13:00–14:00 |
| `afternoon` | 14:00–14:45 |
| `close` | 14:45–15:00 |

### HK

| Session | 本地时间 |
| --- | --- |
| `open` | 09:30–10:00 |
| `morning` | 10:00–12:00 |
| `afternoon_open` | 13:00–14:00 |
| `afternoon` | 14:00–15:30 |
| `close` | 15:30–16:00 |

这些是研究分箱，不等同于交易建议，也没有把某一交易流派的固定时段套到其他市场。

## Day Archetype

当前分类使用已完成交易日的分时数据，采用透明规则并输出 `reasons`：

- `opening_drive_up`
- `opening_drive_down`
- `morning_reversal`
- `late_breakout`
- `trend_up`
- `trend_down`
- `range`
- `insufficient_data`

主要输入包括：

- 日内区间 / ATR20；
- close 在日内区间中的位置；
- ORB 是否最终被突破并保持；
- HOD/LOD 首次形成的大致时间位置。

少于 6 个有效分时点时返回 `insufficient_data`。

**Day archetype 是 ex-post descriptor。** 当前实现用完整日内序列判断最终日型，因此它适合做事后分组和历史条件统计，不能未经额外 point-in-time 实现就直接当成当日早盘可用的实盘 feature。

## Setup Event Definitions

Detector version 为 `setup-detector.v1`。当前只使用事件发生时可知的 level：

- `previous_day_high` / `previous_day_low`
- `previous_5d_high` / `previous_5d_low`
- `opening_range_high` / `opening_range_low`，但仅在 opening range 完成后启用

首版 ORB 可用时间：

- US：10:30 本地时间以后
- CN：10:00 本地时间以后
- HK：10:00 本地时间以后

因此，日终 VWAP 不会参与早盘历史 setup，ORB 也不会在尚未形成时提前“知道”自己的最终 high/low。

容差定义：

```text
max(abs(level) × 0.0005, ATR20 × 0.02)
```

若没有有效 ATR，则只使用价格比例项。

事件：

- `cross_above` / `cross_below`：相邻 bar 穿越 level + tolerance；
- `reclaim_below`：向上穿越后 3 个后续 bar 内重新回到 level - tolerance 下方；
- `reclaim_above`：向下穿越后 3 个后续 bar 内重新回到 level + tolerance 上方；
- `reject_above` / `reject_below`：穿越后的下一 bar 立即回到原侧；
- `break_and_hold_above` / `break_and_hold_below`：连续 3 个 close 保持在 level 的同一外侧。

每个事件记录：

- timestamp / session；
- reference level；
- observed price / tolerance；
- +5m / +15m / +30m forward return；
- 30 分钟 MFE / MAE。

Forward return、MFE、MAE 明确属于 **outcome labels**，当然使用事件之后的数据。它们不进入事件触发条件。Forward return 使用事件时间之后第一个达到目标分钟数的已有 bar，分时粒度不足时对应字段为 `null`。

## Intermarket Context

仅使用同一个 `data.json` 中已有的日线，不新增行情调用。两个标的至少需要 21 个重叠 close，才能得到 20 个 return observations。

每个标的选择绝对相关性最高的可用 peer，并记录：

- `correlation20`
- `relativeStrength20`
- `extremeConfirmation`
- `relativeExtremeDivergence`

极值确认会尊重相关性方向：

- 正相关 peer：主标的新高对应 peer 新高，主标的新低对应 peer 新低；
- 负相关 peer：主标的新高对应 peer 新低，主标的新低对应 peer 新高。

这样 DXY/股指之类的反向关系不会被误判成天然“背离”。这仍然只是普通的相对极值观察，不承担任何特定交易流派的因果解释。

当前 intermarket observation 使用完成后的 daily bars，因此同样属于 ex-post/contextual research。若未来要把它作为实盘 entry filter，需要独立的 point-in-time intraday implementation。

## Event Study

本仓库不在这一层获取经济日历。Enricher 可以接受标准化事件 JSON：

```json
[
  {
    "id": "fomc-2026-07-29",
    "category": "FOMC",
    "importance": "high",
    "timestamp": "2026-07-29 14:00:00"
  }
]
```

执行：

```bash
uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json \
  --events /path/to/events.json
```

只有与标的 `lastTradeDay` 同日的事件会进入研究。当前输出包括事件前 60 分钟、事件后 15/30/60 分钟 return、即时 5 分钟 range、60 分钟 MFE/MAE，以及初始 5 分钟方向是否在 +60m 时反转。

事件供应商、时区标准化和长期事件库应由独立数据或研究流水线负责。

## 前端行为

日内工作台在 `contextualResearch` 合法时显示“市场上下文与 Setup”面板：

- 20 日 HTF 背景；
- day archetype 与原因；
- 参考价位和当前距离；
- session 分箱汇总；
- 最近 setup event 及短期 outcome；
- 跨市场确认；
- 有事件输入时的 event study；
- 条件清单，以及按当前标的隔离的跨日历史统计；
- quality warning。

前端 parser 对缺失、未知版本或结构损坏的 contextual/conditional payload 返回 `null`，不会让主行情页面失效。

条件统计只展示供应方已经计算好的事实，不在浏览器中重算 outcome，也不生成 ICT 或其他流派的综合评分。

发布 workflow 的手动部署入口支持可选的 `contextual_history`（逗号或换行分隔的路径）和
`strategy_outcomes` 输入；两者留空时保持原有单日 enrichment 行为。仓库不在 workflow 中拉取第三方经济日历，
事件仍通过标准化 `--events` 输入提供。

## 当前边界

跨日条件统计的质量取决于历史分时 provider；发布快照中的 `sourceSnapshots`、日期范围和每组
`dateCount` 应作为证据一起审查。策略快照的滚动日期只有在生成器提供 `startDate/endDate`
时才会显示真实日期；如果旧的全市场汇总只提供 per-symbol `foldId`，前端会明确显示“按标的序号”，
不会推断或伪造统一日历日期。
