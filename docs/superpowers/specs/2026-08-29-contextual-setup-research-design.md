# Contextual Setup Research Layer Design

## 背景

当前 Dashboard 已经有两条成熟的数据路径：

1. `data.json` 提供行情、日线、分时、ATR、VWAP、ORB 和价格参考位；
2. `trading_research.strategy_snapshot.v1` 提供跨策略的 coverage、quality、provenance、walk-forward 和 variant metrics。

这两条路径分别回答“市场现在发生了什么”和“策略总体表现如何”，中间缺少一层可复用的研究语义，用来表达：某个 setup 出现时处于什么市场背景、发生在什么时间窗口、接近什么参考价位、由什么可观察事件触发，以及随后产生了怎样的 MFE/MAE/forward return。

ICT 2022 Mentorship 中可借鉴的部分主要是这种研究拆解方式：更高时间框架背景、参考价位、交易时段、触发条件、失效和目标。实现只采纳可观察、可定义、可回测的部分，不把“聪明钱”“机构意图”等叙事写入 contract。

## 目标

本 PR 建立一个策略无关的 contextual research layer，使 Dashboard 可以回答：

- 当前价格相对前一日高低、ORB、VWAP 等参考位处于什么位置；
- 一个分时事件发生在哪个市场 session；
- 当天更接近哪类 day archetype；
- 是否出现 sweep/reclaim/break-and-hold 等可重复检测的 setup event；
- setup 后的 5/15/30 分钟 forward return、MFE 和 MAE；
- 多个标的之间是否出现简单、透明的 relative-extreme divergence；
- 策略结果未来如何按 context/setup 条件做条件化分析；
- FOMC、CPI、NFP、财报等事件如何以统一格式进入 event study，而不把事件供应商耦合进 Dashboard。

## 非目标

- 不实现或宣传 ICT 作为一个新的交易策略；
- 不给主观汇合条件生成“85/100”之类的综合分数；
- 不把特定 ES 点数、纽约 killzone 等教材常数硬编码到所有市场；
- 不在本 PR 新增经济日历第三方 provider；
- 不改变 `trading_research.strategy_snapshot.v1` 的 wire contract；
- 不把原始 minute bars 或大型研究产物提交到 Git。

## 架构

```text
market data / data.json
        ↓
context feature derivation
├── reference levels
├── market session
├── day archetype
├── volatility/range context
└── intermarket confirmation
        ↓
setup event detector
├── cross_above / cross_below
├── reject_above / reject_below
├── reclaim
└── break_and_hold
        ↓
outcome evaluator
├── forward return
├── MFE
└── MAE
        ↓
contextual research snapshot
        ↓
Dashboard contextual research UI
```

共享 schema 和 Python 校验继续放在 `packages/research-core/`。Dashboard Python 负责从自身已有的 `data.json` 语义派生 contextual snapshot；React 只消费产物，不在浏览器重新发明检测规则。

## Contracts

### `trading_research.market_context.v1`

用于描述某个 instrument/date 的上下文：

- instrument identity；
- timezone/market；
- current/close price；
- reference levels；
- session summaries；
- day archetype；
- volatility/range features；
- optional intermarket observations；
- provenance。

Reference level 使用语义化 kind，而不只使用 `support/resistance/key`：

- `previous_day_high`
- `previous_day_low`
- `opening_range_high`
- `opening_range_low`
- `vwap`
- `support`
- `resistance`
- `key`
- `center`

每个 level 可包含 `value`、`distancePct` 和 `sourceLabel`。

### `trading_research.setup_event.v1`

一个 setup event 是可观察事实，不包含交易流派解释。字段包括：

- instrument/date/timestamp；
- session；
- event type；
- reference level；
- observed price；
- threshold/tolerance；
- optional confirmation；
- outcome：`return5m/15m/30m`、`mfe30m`、`mae30m`；
- definition version；
- provenance。

首批 event type：

- `cross_above`
- `cross_below`
- `reject_above`
- `reject_below`
- `reclaim_below`
- `reclaim_above`
- `break_and_hold_above`
- `break_and_hold_below`

其中 reject/reclaim/hold 都必须用明确的 bar 数和 tolerance 定义，避免文字判断。

### `trading_research.event_study.v1`

事件研究 contract 不负责获取日历，只负责接受已经标准化的事件：

- event id/category/importance/timestamp；
- instrument；
- pre/post window；
- pre-event range/return；
- immediate range；
- post-event forward returns；
- MFE/MAE；
- optional initial-move reversal flag；
- provenance。

这样未来可以由独立 provider、手工 fixture 或研究流水线提供 FOMC/CPI/NFP/earnings 数据。

## Session model

Session 定义按 market + instrument timezone 配置，而不是复刻教材中的固定美东时间。

US 默认：

- `premarket`: 04:00-09:30
- `opening_range`: 09:30-10:30
- `morning`: 10:30-12:00
- `midday`: 12:00-13:30
- `afternoon`: 13:30-15:00
- `power_hour`: 15:00-16:00

CN 默认：

- `open`: 09:30-10:00
- `morning`: 10:00-11:30
- `afternoon_open`: 13:00-14:00
- `afternoon`: 14:00-14:45
- `close`: 14:45-15:00

HK 默认：

- `open`: 09:30-10:00
- `morning`: 10:00-12:00
- `afternoon_open`: 13:00-14:00
- `afternoon`: 14:00-15:30
- `close`: 15:30-16:00

配置是纯数据，检测代码不依赖某个市场的 session 名称。

## Day archetype

首版只使用当前 Dashboard 已有日线/分时数据，采用透明规则而不是聚类黑盒。支持：

- `trend_up`
- `trend_down`
- `range`
- `opening_drive_up`
- `opening_drive_down`
- `morning_reversal`
- `late_breakout`
- `insufficient_data`

规则由 range/ATR、open-to-close location、ORB break、HOD/LOD 时间和 VWAP/开盘关系组合得到。分类结果必须同时输出 `reasons`，UI 不显示一个无法解释的标签。

## Intermarket context

首版只做同一 Dashboard snapshot 内标的间的透明比较，不引入新的行情源。

提供：

- 20-bar return relative strength；
- 20-bar rolling return correlation；
- 同期新高/新低是否被对方确认；
- `relative_extreme_divergence` observation。

默认只在双方有足够重叠 daily bars 时计算。不存在人为“SMT score”。

## Dashboard 输出

Dashboard generator 在顶层增加 optional `contextualResearch`，旧 `data.json` 仍然合法。该字段包含：

- schema version；
- generatedAt；
- per-instrument market contexts；
- setup events；
- event studies（默认可为空）；
- quality/coverage/provenance。

这样不需要新增一个必须同步发布的第四个静态文件，也不会让缺少 contextual research 导致主行情工作区失效。

## 前端

新增 `ContextualResearchPanel`，放在选中标的的日内工作台内，展示：

1. **Context**：day archetype、当前 session、range/ATR、与关键 reference level 的距离；
2. **Reference Levels**：语义化 PDH/PDL/ORB/VWAP 等；
3. **Setup Events**：最近事件、触发时间、reference level、5/15/30m 结果、MFE/MAE；
4. **Intermarket**：可用时展示 relative strength/correlation/divergence；
5. **Event Study**：只有 snapshot 内确有事件时才显示。

不引入综合 confluence score。条件组合研究用真实样本数和 outcome metrics 表示。

## 兼容和失败边界

- `contextualResearch` 完全 optional；旧 demo snapshot 和旧 producer 继续工作；
- schema 不支持、单个 instrument 计算失败或 bars 不足时，记录 coverage/quality warning，不阻断行情页面；
- 无 intraday 时仍可生成 reference levels、daily range context 和 intermarket daily features；setup events 为空；
- 所有时间计算使用 instrument timezone；前端不自行猜时区。

## 测试

### Research core

- 三个 JSON Schema 的 valid/invalid fixtures；
- validator/load helper 单测；
- contract version 常量测试。

### Dashboard Python

- session boundary 测试；
- semantic reference level derivation；
- sweep/reclaim/break-and-hold deterministic fixture；
- forward return/MFE/MAE；
- day archetype transparent rule fixtures；
- intermarket correlation/divergence；
- 无 intraday/短数据 graceful degradation；
- generator 输出 optional contextualResearch。

### Frontend

- parser 对 optional/malformed contextual snapshot 的容错；
- ContextualResearchPanel 渲染；
- 空态；
- 现有页面无 contextualResearch 时回归；
- build/typecheck/e2e 不产生横向溢出。

## 文档

更新：

- `packages/research-core/README.md`
- `apps/dashboard/docs/outputs.md`
- `apps/dashboard/docs/indicators.md`
- `apps/dashboard/docs/web-frontend.md`
- `docs/roadmap/README.md`

明确区分“已实现 detector/contract”和“仍需外部事件 provider/长期统计样本”的边界。

## 回滚

所有新增字段都是 optional。回滚可直接撤销 contextual research generator、React panel 和三个新 schema；现有 `data.json`、`research.json`、`rbreaker-research.json` 以及 `strategy_snapshot.v1` 不需要迁移或降级。