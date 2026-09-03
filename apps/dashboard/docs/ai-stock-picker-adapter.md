# AI Stock Picker Canonical Adapter

Dashboard 通过 `trading_research.ai_stock_picker_adapter` 消费经过 owner validation 的 `ai-stock-picker` selection，并投影为 Research Core canonical records。

该 adapter 不执行选股、不调用 LLM、不读取凭据，也不复制 `ai-stock-picker` 的完整 Pydantic schema。

## 上游要求

上游必须先由 `ai-stock-picker` owner validator 验证 selection，并生成 content-bound validation receipt。

Producer 对应能力当前位于 `ai-stock-picker` PR #109。预期调用形式：

```bash
uv run aipick cn validate \
  --selection /absolute/path/selection.json \
  --candidates /absolute/path/candidates.json \
  --validation-receipt
```

若同时拥有 append-only evidence：

```bash
uv run aipick cn validate \
  --selection /absolute/path/selection.json \
  --candidates /absolute/path/candidates.json \
  --evidence-dir /absolute/path/selection.json.evidence \
  --validation-receipt
```

Dashboard 不接受旧的、未绑定 selection digest 的 `{ "valid": true }` validation summary。

## Python API

```python
from trading_research.ai_stock_picker_adapter import adapt_ai_stock_picker_selection

agent_run, evidence = adapt_ai_stock_picker_selection(
    selection_path.read_bytes(),
    validation_receipt,
    adapted_at="2026-09-03T09:15:00Z",
)
```

`adapted_at` 必须由调用方显式传入。adapter 不读取系统时钟，因此同一输入可确定性 replay。

## Receipt handshake

第一版只支持：

- receipt `schema_version = 1.0.0`；
- `artifact_type = ai_stock_selection_validation_receipt`；
- `valid = true`；
- `validation_profile = current_full`；
- prompt hash 和 commentary policy 都已由 owner 重新校验；
- receipt 的 `selection_sha256` 必须等于当前 selection 原始字节的 SHA-256；
- market、selection as-of、prompt version、pick count 必须与 selection 一致。

Response evidence 只允许两种强度：

- `format_only_raw_response_unavailable`：没有 byte-exact provider response evidence；
- `byte_exact_evidence`：必须同时提供合法 `evidence_manifest_sha256`。

format-only receipt 若携带 evidence manifest hash、或 byte-exact receipt 缺少 manifest hash，都会 fail closed。

## Canonical 输出

adapter 返回两份独立可变对象：

1. `trading_research.agent_run.v1`
2. `trading_research.research_evidence.v1`

两份对象在返回前都会通过 `research-core` validator。

### Agent Run

- `status = completed`；
- `completedAt` 使用 owner selection 的 `generated_at`；
- 不生成 `startedAt`；
- `budget = {}`、`usage = {}`、`tasks = []`；
- model provider/name 来自 owner selection；
- harness 为 `ai-stock-picker`；
- run ID 由完整 selection SHA-256 确定。

空 budget/usage/tasks 是刻意的。selection artifact 没有可靠记录调用开始时间、token、成本、latency、worker iteration 等字段，adapter 不为满足 canonical schema 编造这些数据。

### Research Evidence

- `verificationStatus = verified` 表示匹配的 owner validation receipt 已通过 adapter handshake；
- `contentSha256` 是 selection 文件原始字节 SHA-256；
- `dataAsOf` 使用 selection `data_cutoff`；
- `retrievedAt` 使用显式 `adapted_at`；
- Point-in-time assurance、strict flag、OOS eligibility 原样传播；
- producer `evidence_limitations` 原样保留。

format-only response receipt 会额外加入：

```text
provider_response_not_byte_exact_revalidated
```

byte-exact evidence 不加入该 limitation。

## Provenance

canonical provenance 记录：

- owner selection schema version；
- owner validation receipt schema version/profile；
- selection SHA-256；
- evidence manifest SHA-256（如有）；
- candidate input/symbol hashes；
- prompt/response hashes；
- prompt version；
- selection method；
- response hash verification strength。

这些 hash 用于内容 identity 和跨 artifact 绑定。它们不证明某份内容在历史时间点已经存在。

## PIT / OOS 边界

adapter 不升级任何 evidence 资格。

`strict_point_in_time=false` 会保持 false；`eligible_as_oos_evidence=false` 会保持 false。即便拥有 byte-exact provider response evidence，也只加强运行归档完整性，不自动建立严格 Point-in-time 或样本外有效性。

## 当前范围

第一版不生成：

- `research_experiment.v1`；
- `eval_result.v1`；
- forward return / IC / drawdown；
- Dashboard AI Research UI；
- publication workflow。

Experiment/Eval 需要独立的实验注册和未来结果标签，不能由 selection adapter 猜出来。

## 合并依赖

本 Dashboard PR 在 producer PR #109 完成 `ai-stock-picker` 仓库要求的本地完整检查并合入前保持 Draft。
