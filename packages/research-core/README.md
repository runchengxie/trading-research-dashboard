# Research Core

`packages/research-core/` 是共享研究契约的 canonical 位置，当前承载 `niu_men.research_snapshot.v2` 的：

- JSON Schema：`src/research_core/schemas/research-snapshot.schema.json`，以 package data 形式随包分发
- fixture：`tests/fixtures/research_snapshot/`
- 结构校验：`validate_snapshot()` 与 `load_snapshot()`
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
- 完整 OOS 研究产物

根目录、Dashboard 和 Niu Men 各保留一份 schema/fixture 兼容镜像，由根级 `tests/test_research_contract_sync.py` 强制与 canonical 一致；镜像收敛留待后续评估。

Niu Men 已通过 uv workspace 本地源依赖本包，其 `scripts/snapshot_contract.py` 是指向 `research_core.snapshot` 的兼容 wrapper。Dashboard Python 暂无共享包依赖需求。
