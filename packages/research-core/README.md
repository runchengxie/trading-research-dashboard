# Research Core

`packages/research-core/` 是共享研究契约的 canonical 位置，当前承载：

- `niu_men.research_snapshot.v2`：Niu Men 历史研究快照；
- `trading_research.strategy_snapshot.v1`：跨策略 OOS/variant 汇总 envelope；
- `trading_research.market_context.v1`：策略无关的市场上下文；
- `trading_research.setup_event.v1`：可观察 setup 事件；
- `trading_research.event_study.v1`：标准化事件研究；
- `trading_research.contextual_snapshot.v1`：Dashboard contextual research 聚合快照；
- `trading_research.conditional_research.v1`：跨多个 contextual snapshot 的条件统计汇总；
- `trading_research.research_experiment.v1`：可重复比较的研究实验、baseline、variants 与 scorecard 定义；
- `trading_research.agent_run.v1`：vendor-neutral 的 Agent/Harness 运行摘要、task graph、资源消耗和 artifact/evidence 引用；
- `trading_research.research_evidence.v1`：带来源、hash、时点保证与限制的 canonical 研究证据记录；
- `trading_research.eval_result.v1`：将 experiment/case/run/variant 绑定到 scorecard 指标结果。

Contextual contracts 只描述可观察、可定义、可回测的事实，例如参考价位、session、day archetype、cross/reclaim/break-and-hold、forward return、MFE/MAE 和跨标的确认。它们不承载“机构意图”、交易流派叙事或主观 confluence score。

Experiment / Agent Run / Evidence / Eval contracts 用于统一不同研究 producer 的运行与评估语义。详细 Prompt、provider 原始响应、工具原始结果、大型回测产物和其他 producer-owned archive 继续由 producer 自己管理；`research-core` 只保存可公开审查的 canonical wire record 和引用，不保存隐藏 chain-of-thought。

`research_evidence.v1` 对 Point-in-time 与 OOS 标志采用保守校验。文件 hash 只能证明内容 identity，producer 自报时间也不能单独建立严格历史存在证明；contract 本身不会把一条 evidence 自动提升为严格 PIT 或正式 OOS 证据。

共享包提供：

- JSON Schema：`src/research_core/schemas/`
- 结构校验：`validate_snapshot()`、`validate_strategy_snapshot()`、`validate_market_context()`、`validate_setup_event()`、`validate_event_study()`、`validate_contextual_snapshot()`、`validate_conditional_research()`、`validate_research_experiment()`、`validate_agent_run()`、`validate_research_evidence()`、`validate_eval_result()`
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
- 外部 Agent Harness 的完整运行时、原始 Prompt 或 provider response archive

根目录、Dashboard 和 Niu Men 对历史 `research-snapshot` 仍保留兼容镜像，由根级 `tests/test_research_contract_sync.py` 强制同步。新增 contextual contracts 与 research run contracts 只在 `research-core` 保留 canonical schema，Dashboard 或外部 producer 通过 workspace 依赖、adapter 或经过验证的 publication projection 调用 validator。
