# Research Core

`packages/research-core/` 是共享研究契约的 canonical 位置，当前承载：

- `niu_men.research_snapshot.v2`：Niu Men 历史研究快照；
- `trading_research.strategy_snapshot.v1`：跨策略 OOS/variant 汇总 envelope；
- `trading_research.market_context.v1`：策略无关的市场上下文；
- `trading_research.setup_event.v1`：可观察 setup 事件；
- `trading_research.event_study.v1`：标准化事件研究；
- `trading_research.contextual_snapshot.v1`：Dashboard contextual research 聚合快照。
- `trading_research.conditional_research.v1`：跨多个 contextual snapshot 的条件统计汇总。

Contextual contracts 只描述可观察、可定义、可回测的事实，例如参考价位、session、day archetype、cross/reclaim/break-and-hold、forward return、MFE/MAE 和跨标的确认。它们不承载“机构意图”、交易流派叙事或主观 confluence score。

共享包提供：

- JSON Schema：`src/research_core/schemas/`
- 结构校验：`validate_snapshot()`、`validate_strategy_snapshot()`、`validate_market_context()`、`validate_setup_event()`、`validate_event_study()`、`validate_contextual_snapshot()`、`validate_conditional_research()`
- loader：`load_snapshot()`、`load_strategy_snapshot()`、`load_contextual_snapshot()`
- provenance 规则：`missing_provenance_fields()`、`provenance_complete()`、`validate_provenance_consistency()`

## 本地验证

```bash
cd packages/research-core
uv run pytest -q
uv run ruff check src tests
```

仓库是统一 uv workspace：锁文件只有根目录的 `uv.lock`，成员目录不再生成或提交嵌套锁文件。

这里不应放入：

- Niu Men 指标和信号逻辑
- R-Breaker 策略实现
- Dashboard React 组件
- 行情抓取和本地数据归档
- 经济日历 provider
- 完整 OOS 研究产物

根目录、Dashboard 和 Niu Men 对历史 `research-snapshot` 仍保留兼容镜像，由根级 `tests/test_research_contract_sync.py` 强制同步。新增 contextual contracts 只在 `research-core` 保留 canonical schema，Dashboard 通过 workspace 依赖调用 validator。
