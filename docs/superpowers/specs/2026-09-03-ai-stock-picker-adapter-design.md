# AI Stock Picker Canonical Adapter 设计

## 背景

`research-core` 已提供 `agent_run.v1` 与 `research_evidence.v1`。`ai-stock-picker` 继续拥有候选池、Prompt、provider、selection schema、append-only evidence 和 owner validation。Dashboard 不复制其 Pydantic schema，也不直接执行选股逻辑。

`ai-stock-picker` Draft PR #109 定义 `ai_stock_selection_validation_receipt.v1` 风格的内容绑定凭据：receipt 包含 `selection_sha256`，用于证明 owner validator 验证的是当前传给 adapter 的 selection 文件字节。

## 目标

在 Dashboard app 层新增纯 adapter：

```python
adapt_ai_stock_picker_selection(
    selection_bytes: bytes,
    validation_receipt: Mapping[str, Any],
    *,
    adapted_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]
```

返回：

1. `trading_research.agent_run.v1`
2. `trading_research.research_evidence.v1`

`adapted_at` 由调用方显式传入，adapter 不读取系统时钟，因此 replay 结果确定。

## 非目标

本 PR 不：

- 调用 `aipick` CLI 或 provider；
- 读取 API key；
- 复制 `ai-stock-picker` 的 selection schema；
- 生成 `research_experiment.v1`；
- 生成 `eval_result.v1`；
- 做 forward return、IC、drawdown 或其他效果评估；
- 接入 Dashboard React 页面；
- 发布外部 artifact；
- 升级任何 PIT/OOS 资格。

## 输入握手

第一版只接受当前 owner selection 与 validation receipt：

### Selection

必须至少满足：

- `schema_version == "1.0.0"`
- `artifact_type == "ai_stock_selection"`
- `selection_method == "llm_candidate_rerank"`
- `market`、`provider`、`model`、`prompt_version` 为非空字符串
- `generated_at`、`data_cutoff` 为非空字符串
- `strict_point_in_time`、`eligible_as_oos_evidence` 为布尔值
- `point_in_time_assurance` 属于 canonical assurance enum
- `evidence_limitations` 为非空字符串数组
- `lineage` 包含四个 64 位小写 SHA-256：`input_sha256`、`candidate_symbols_sha256`、`prompt_sha256`、`response_sha256`
- `picks` 为数组

这些检查只确认 adapter 需要的字段存在且类型可安全投影，不重新实现 owner 的完整 selection validator。

### Validation receipt

第一版固定支持：

- `schema_version == "1.0.0"`
- `artifact_type == "ai_stock_selection_validation_receipt"`
- `valid is True`
- `validation_profile == "current_full"`
- `prompt_hash_revalidated is True`
- `commentary_policy_revalidated is True`
- `selection_sha256` 为当前 `selection_bytes` 的 SHA-256
- `market == selection.market`
- `selection_as_of == selection.selection_as_of`
- `prompt_version == selection.prompt_version`
- `picks == len(selection.picks)`
- `response_sha256_verification` 为 `format_only_raw_response_unavailable` 或 `byte_exact_evidence`
- `evidence_manifest_sha256` 为 `null` 或合法 SHA-256

receipt 与 selection 任一 identity 不一致即 fail closed。

## Agent Run 映射

```text
schemaVersion   = trading_research.agent_run.v1
runId           = ai-stock-picker:<selection_sha256>
status          = completed
completedAt     = selection.generated_at
model.provider  = selection.provider
model.name      = selection.model
harness.name    = ai-stock-picker
budget          = {}
usage           = {}
tasks           = []
artifactRefs    = [artifact://ai-stock-picker/selection/<selection_sha256>]
evidenceRefs    = [ai-stock-picker-selection:<selection_sha256>]
limitations     = conservative limitations
provenance      = owner lineage + receipt identity
```

不生成 run-level `startedAt`，因为 owner selection 没有可靠记录模型调用开始时间。

`tasks=[]` 是刻意设计：selection artifact 不可靠记录 worker/task iterations 或 task start time，adapter 不应编造一次“rerank task”。

## Research Evidence 映射

```text
schemaVersion        = trading_research.research_evidence.v1
evidenceId           = ai-stock-picker-selection:<selection_sha256>
runId                = ai-stock-picker:<selection_sha256>
evidenceType         = ai_stock_selection
retrievedAt          = adapted_at
dataAsOf              = selection.data_cutoff
freshnessStatus       = unknown
verificationStatus    = verified
artifactRef           = artifact://ai-stock-picker/selection/<selection_sha256>
contentSha256         = selection_sha256
pointInTime.assurance = selection.point_in_time_assurance
pointInTime.strict    = selection.strict_point_in_time
eligibleAsOosEvidence = selection.eligible_as_oos_evidence
limitations           = conservative limitations
provenance            = owner lineage + receipt identity
```

`source.provider = "ai-stock-picker"`，`source.sourceType = "validated_selection_artifact"`，`source.method = "owner_validation_receipt"`。

## 限制传播

selection 的 `evidence_limitations` 原样进入 run/evidence limitations。

若 receipt 的 `response_sha256_verification != "byte_exact_evidence"`，额外加入：

```text
provider_response_not_byte_exact_revalidated
```

若 receipt 已是 `byte_exact_evidence`，不添加该限制。

adapter 不删除 producer 已声明的 limitation。

## Provenance

两类 canonical record 至少记录：

```text
source = ai-stock-picker
ownerSelectionSchemaVersion
ownerValidationReceiptSchemaVersion
ownerValidationProfile
selectionSha256
evidenceManifestSha256
inputSha256
candidateSymbolsSha256
promptSha256
responseSha256
promptVersion
selectionMethod
responseSha256Verification
```

`evidenceManifestSha256` 可以为 `null`，表示没有使用 append-only evidence 目录做 byte-exact response revalidation。

## 验证

adapter 生成结果后必须调用：

```python
validate_agent_run(agent_run)
validate_research_evidence(evidence)
```

canonical validator 失败时 adapter 失败，不返回半合法结果。

## 依赖边界

Dashboard adapter 只依赖 `research-core`。它不依赖 `ai-stock-picker` Python package。

Producer PR #109 在合入前仍需在 `ai-stock-picker` 本地运行：

```bash
uv run python scripts/dev/check.py
```

Dashboard adapter PR 可以先作为 Draft 通过自身 CI，但在 producer receipt contract 尚未验证并合入前不应合并。
