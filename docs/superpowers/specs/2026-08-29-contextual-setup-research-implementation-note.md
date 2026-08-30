# Contextual Setup Research Implementation Note

本记录说明 `2026-08-29-contextual-setup-research-design.md` 与最终实现之间一个有意的边界调整。

## Generator 集成方式

原设计写的是由 `trading_research.dashboard.astock_tech` 在生成 `data.json` 时直接增加 optional `contextualResearch`。

实现阶段改为独立的后置 enrichment：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --codes sz300246,AAPL.US,TSLA.US \
  --json web/public/data.json

uv run python -m trading_research.scripts.enrich_contextual_research \
  --input web/public/data.json
```

Enricher 默认原子覆盖输入，也支持 `--output` 写入另一文件，以及 `--events` 接受标准化事件 JSON。

## 调整原因

1. **兼容性更强**：现有 `astock_tech.py`、CLI 调用方、静态 fallback 和部署流程不需要同时迁移；旧 `data.json` 保持合法。
2. **失败隔离**：contextual detector、intermarket 或 event study 的问题不会影响行情抓取和基础快照生成。
3. **事件输入边界清楚**：经济/公司事件属于可选研究输入，不需要污染行情 generator 的稳定调用签名。
4. **回滚简单**：移除 enrichment 步骤即可恢复原有发布行为，不需要修改基础 generator。
5. **便于历史回填**：已有 `data.json` 可以离线 enrichment，无需再次调用行情 provider。

## 保持不变的设计约束

- 输出字段仍是 `data.json.contextualResearch`，没有新增第四个必须部署的静态文件；
- `contextualResearch` 仍然 optional；
- `trading_research.strategy_snapshot.v1` 未改变；
- React 只消费 contextual snapshot，不在浏览器实现 detector；
- 单个 contextual instrument 失败只产生 quality warning；
- 不引入 ICT score、主观机构叙事或第三方经济日历 provider。

## 长期条件统计

当前 Dashboard 静态行情只保存上一交易日分时，因此本 PR 展示单快照 setup event 和 forward outcome。跨多日的条件 expectancy、胜率和样本数必须基于真实保留的多日 contextual snapshots。

现有 contract 和 detector 已为这类汇总提供稳定输入。未来应增加独立 history summarizer / research artifact，而不是在当前单日快照上伪造统计样本。
