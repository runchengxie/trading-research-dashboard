# Research Core

`packages/research-core/` 是共享研究契约的 canonical 位置，当前承载 `niu_men.research_snapshot.v2` 的：

- JSON Schema：`src/research_core/schemas/research-snapshot.schema.json`，以 package data 形式随包分发
- fixture：`tests/fixtures/research_snapshot/`
- 结构校验：`validate_snapshot()` 与 `load_snapshot()`
- provenance 规则：`missing_provenance_fields()`、`provenance_complete()`、`validate_provenance_consistency()`

## 本地验证

```bash
cd packages/research-core
uv run --project . --group dev pytest -q
uv run --project . --group dev ruff check src tests
```

M2 不提交本包的 `uv.lock`；`uv run` 可能生成它，提交前应删除。根 `.gitignore` 已包含对应条目。

这里不应放入：

- Niu Men 指标和信号逻辑
- R-Breaker 策略实现
- Dashboard React 组件
- 行情抓取和本地数据归档
- 完整 OOS 研究产物

根目录、Dashboard 和 Niu Men 各保留一份 schema/fixture 兼容镜像，由根级 `tests/test_research_contract_sync.py` 强制与 canonical 一致；镜像收敛属于后续 M3 workspace 工作。

注意：Niu Men 与 Dashboard 的 Python 代码尚未 import `research_core`。在 M3 建立本地 package 依赖之前，不要宣称生产代码已使用本包。
