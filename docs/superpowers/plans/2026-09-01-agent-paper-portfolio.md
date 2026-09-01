# Agent 纸面组合实验实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Dashboard 中加入一个使用 `GLM-4.7-Flash` 的低频纸面组合实验，并通过 GitHub Actions 生成可审计的静态净值数据。

**Architecture:** `research-core` 提供版本化 Agent 组合合同和纯函数校验。Dashboard Python 包提供智谱 API 客户端、目标权重模拟器和快照生成命令。GitHub Actions 负责定时编排，前端读取 `public/agent/` 下的独立静态文件。

**Tech Stack:** Python 3.11、uv workspace、Pydantic、标准库 HTTP、pytest、jsonschema、React、TypeScript、ECharts、pnpm、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-09-01-agent-paper-portfolio-design.md`

## Global Constraints

- 只支持 long-only、无杠杆、无做空的纸面组合。
- 模型只生成目标权重和说明，成交、手续费、NAV 和回撤由确定性代码计算。
- API key 只从 `ZHIPU_API_KEY` 读取，不写入日志、快照或 artifact。
- 不接券商、不发送真实订单、不使用 Codex CLI 作为生产调度器。
- 现有 `data.json`、研究快照合同和页面保持兼容。
- 失败运行不得覆盖上一份有效 Agent 快照。
- 新增 workflow 使用 `contents: read`，默认只上传 artifact。
- 所有新增行为先写失败测试，再写最小实现。

---

### Task 1: 定义 Agent 组合合同

**Files:**
- Create: `packages/research-core/src/research_core/agent_portfolio.py`
- Create: `packages/research-core/src/research_core/schemas/agent-portfolio.v1.schema.json`
- Create: `packages/research-core/tests/test_agent_portfolio.py`
- Modify: `packages/research-core/src/research_core/__init__.py`
- Modify: `packages/research-core/pyproject.toml` if package data needs the schema included

**Interfaces:**
- Produce `AGENT_PORTFOLIO_VERSION = "trading_research.agent_portfolio.v1"`.
- Produce `validate_agent_portfolio(payload: Mapping[str, Any]) -> None`.
- Produce `load_agent_portfolio(path: str | Path) -> dict[str, Any]`.
- Produce `validate_target_weights(weights: Mapping[str, Any], allowed_symbols: Collection[str], max_position_weight: float, min_cash_weight: float) -> dict[str, float]`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_valid_agent_portfolio_is_accepted() -> None:
    payload = json.loads((FIXTURE_ROOT / "valid.json").read_text(encoding="utf-8"))
    validate_agent_portfolio(payload)

def test_agent_portfolio_rejects_wrong_version() -> None:
    payload = json.loads((FIXTURE_ROOT / "valid.json").read_text(encoding="utf-8"))
    payload["schemaVersion"] = "trading_research.agent_portfolio.v9"
    with pytest.raises(ValueError, match="agent portfolio schema validation failed"):
        validate_agent_portfolio(payload)

def test_target_weights_reject_unknown_symbol_and_excess_weight() -> None:
    with pytest.raises(ValueError, match="unknown symbol"):
        validate_target_weights({"NVDA": 0.2}, {"SPY", "CASH"}, 0.6, 0.1)
```

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run: `uv run --locked --package research-core pytest packages/research-core/tests/test_agent_portfolio.py -q`

Expected: FAIL because the new contract functions and schema do not exist.

- [ ] **Step 3: Add the JSON Schema and validation functions**

The schema must require `schemaVersion`, `generatedAt`, `asOf`, `agent`, `portfolio`, `metrics`, `decision`, `positions`, `trades`, and `history`. Set `additionalProperties` to `false` for model-controlled decision objects. Keep financial numbers finite and require `CASH` in normalized target weights.

- [ ] **Step 4: Run focused tests and the existing research-core tests**

Run: `uv run --locked --package research-core pytest packages/research-core/tests/test_agent_portfolio.py packages/research-core/tests/test_snapshot.py -q`

Expected: all focused and existing contract tests pass.

- [ ] **Step 5: Commit the contract**

```bash
git add packages/research-core/src/research_core packages/research-core/tests/test_agent_portfolio.py packages/research-core/pyproject.toml
git commit -m "feat: add agent portfolio contract"
```

### Task 2: Implement the deterministic paper simulator

**Files:**
- Create: `apps/dashboard/src/trading_research/agent_portfolio.py`
- Create: `apps/dashboard/tests/test_agent_portfolio.py`

**Interfaces:**
- Produce immutable-friendly dataclasses `Position`, `Trade`, and `PaperPortfolioState`.
- Produce `simulate_rebalance(previous: PaperPortfolioState | None, target_weights: Mapping[str, float], prices: Mapping[str, float], as_of: str, initial_equity: float, fee_rate: float, max_position_weight: float, min_cash_weight: float) -> PaperPortfolioState`.
- Use close prices for all paper fills and record `priceSource="close"`.

- [ ] **Step 1: Write failing simulator tests**

```python
def test_first_run_allocates_cash_and_records_buy_trades() -> None:
    state = simulate_rebalance(
        None,
        {"SPY": 0.5, "CASH": 0.5},
        {"SPY": 100.0},
        "2026-09-01",
        100_000.0,
        0.001,
        0.8,
        0.1,
    )
    assert state.equity == pytest.approx(99_950.0)
    assert state.positions["SPY"].market_value == pytest.approx(49_950.0)
    assert state.cash == pytest.approx(49_950.0)
    assert len(state.trades) == 1

def test_rebalance_sells_and_buys_using_current_equity() -> None:
    previous = PaperPortfolioState(
        as_of="2026-09-01",
        initial_equity=100_000.0,
        equity=100_000.0,
        cash=50_000.0,
        positions={"SPY": Position(symbol="SPY", shares=500, market_value=50_000.0)},
        history=(),
        trades=(),
    )
    state = simulate_rebalance(
        previous,
        {"QQQ": 0.4, "CASH": 0.6},
        {"SPY": 110.0, "QQQ": 200.0},
        "2026-09-02",
        100_000.0,
        0.001,
        0.8,
        0.1,
    )
    assert state.positions["SPY"].shares == 0
    assert state.positions["QQQ"].market_value > 0

def test_missing_price_rejects_the_rebalance() -> None:
    with pytest.raises(ValueError, match="missing price"):
        simulate_rebalance(None, {"SPY": 0.8, "CASH": 0.2}, {}, "2026-09-01", 100_000, 0, 0.8, 0.1)
```

- [ ] **Step 2: Run the simulator tests and verify failure**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_agent_portfolio.py -q`

Expected: FAIL because the simulator module does not exist.

- [ ] **Step 3: Implement minimal long-only execution and metrics**

Use integer shares, reserve cash for fees, discard trades below one share, calculate equity from cash plus marked-to-market positions, and append one history point per run. Calculate `nav = equity / initialEquity`, cumulative return, and running maximum drawdown without pandas.

- [ ] **Step 4: Run focused and package tests**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_agent_portfolio.py -q`

Expected: all simulator tests pass.

- [ ] **Step 5: Commit the simulator**

```bash
git add apps/dashboard/src/trading_research/agent_portfolio.py apps/dashboard/tests/test_agent_portfolio.py
git commit -m "feat: add deterministic paper portfolio simulator"
```

### Task 3: Add the GLM client and decision pipeline

**Files:**
- Create: `apps/dashboard/src/trading_research/agent_decision.py`
- Create: `apps/dashboard/tests/test_agent_decision.py`
- Modify: `apps/dashboard/pyproject.toml` only if a locked HTTP client dependency is required

**Interfaces:**
- Produce `GLMModelClient(api_key: str, model: str = "glm-4.7-flash", endpoint: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions")`.
- Produce `GLMModelClient.complete_decision(context: Mapping[str, Any], prompt_version: str) -> AgentDecision`.
- Produce `AgentDecision(target_weights: dict[str, float], reasoning_summary: str, provider: str, model: str, prompt_version: str, input_hash: str)`.
- Use standard-library `urllib.request` so the dashboard package does not gain an unnecessary runtime dependency.

- [ ] **Step 1: Write failing response parsing tests**

```python
def test_client_parses_json_decision_from_model_response() -> None:
    decision = parse_model_response(
        '{"target_weights":{"SPY":0.8,"CASH":0.2},"reasoning_summary":"trend"}',
        allowed_symbols={"SPY", "CASH"},
    )
    assert decision.target_weights == {"SPY": 0.8, "CASH": 0.2}

def test_client_rejects_invalid_model_json() -> None:
    with pytest.raises(ValueError, match="model response"):
        parse_model_response("not json", allowed_symbols={"SPY", "CASH"})

def test_prompt_hash_changes_when_context_changes() -> None:
    assert build_input_hash({"price": 100}) != build_input_hash({"price": 101})
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_agent_decision.py -q`

Expected: FAIL because the parser and client module do not exist.

- [ ] **Step 3: Implement request construction and strict response parsing**

Send a system instruction requiring one JSON object with `target_weights` and `reasoning_summary`. Set a small output limit, disable unnecessary tool behavior, and include the allowed symbols and current portfolio in the user context. Strip a single fenced JSON block if present, then parse and validate it through the contract helper. Never log the API key or full model response.

- [ ] **Step 4: Test the HTTP boundary without network access**

Inject a transport callable into `GLMModelClient` and test request headers, model name, timeout handling, non-200 errors, and successful parsing with fixtures.

- [ ] **Step 5: Run focused tests and commit**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_agent_decision.py -q`

```bash
git add apps/dashboard/src/trading_research/agent_decision.py apps/dashboard/tests/test_agent_decision.py apps/dashboard/pyproject.toml uv.lock
git commit -m "feat: add glm paper decision client"
```

### Task 4: Add snapshot generation command and fixtures

**Files:**
- Create: `apps/dashboard/src/trading_research/scripts/generate_agent_portfolio.py`
- Create: `apps/dashboard/tests/test_generate_agent_portfolio.py`
- Create: `apps/dashboard/tests/fixtures/agent_portfolio/previous.json`
- Create: `apps/dashboard/tests/fixtures/agent_portfolio/prices.json`
- Create: `apps/dashboard/tests/fixtures/agent_portfolio/model-response.json`
- Create: `apps/dashboard/tests/fixtures/agent_portfolio/expected-latest.json`
- Modify: `apps/dashboard/pyproject.toml` to add `agent-portfolio = "trading_research.scripts.generate_agent_portfolio:main"`

**Interfaces:**
- CLI: `agent-portfolio --prices PATH --previous PATH --model-response PATH --output PATH --as-of YYYY-MM-DD --generated-at ISO8601`.
- The command must support an offline `--model-response` fixture path for tests and local replay.
- The generated output must include the new contract version, provenance, decision, trades, positions, metrics, and history.

- [ ] **Step 1: Write failing generator tests**

```python
def test_generator_builds_valid_latest_snapshot(tmp_path: Path) -> None:
    output = tmp_path / "latest.json"
    generate_snapshot(
        prices_path=FIXTURE_ROOT / "prices.json",
        previous_path=FIXTURE_ROOT / "previous.json",
        model_response_path=FIXTURE_ROOT / "model-response.json",
        output=output,
        as_of="2026-09-01",
        generated_at="2026-09-01T22:00:00Z",
    )
    payload = json.loads(output.read_text())
    validate_agent_portfolio(payload)
    assert payload["portfolio"]["nav"] == pytest.approx(1.0)

def test_generator_does_not_replace_output_when_validation_fails(tmp_path: Path) -> None:
    output = tmp_path / "latest.json"
    output.write_text('{"reviewed": true}\n')
    with pytest.raises(ValueError):
        generate_snapshot(
            prices_path=FIXTURE_ROOT / "prices.json",
            previous_path=FIXTURE_ROOT / "previous.json",
            model_response_path=FIXTURE_ROOT / "malformed-response.json",
            output=output,
            as_of="2026-09-01",
            generated_at="2026-09-01T22:00:00Z",
        )
    assert output.read_text() == '{"reviewed": true}\n'
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_generate_agent_portfolio.py -q`

Expected: FAIL because the command and fixture builder do not exist.

- [ ] **Step 3: Implement atomic offline generation**

Load the previous state, prices and model response, run the parser and simulator, validate the complete output, then write through a temporary file in the destination directory and replace the destination atomically. Update `history.json` and `decisions.json` only after `latest.json` validates.

- [ ] **Step 4: Run fixture tests and command help**

Run: `uv run --locked --package trading-research-dashboard-app pytest apps/dashboard/tests/test_generate_agent_portfolio.py -q` and `uv run --locked --package trading-research-dashboard-app agent-portfolio --help`.

Expected: tests pass and CLI help lists all required paths.

- [ ] **Step 5: Commit the offline pipeline**

```bash
git add apps/dashboard/src/trading_research/scripts apps/dashboard/tests/fixtures/agent_portfolio apps/dashboard/tests/test_generate_agent_portfolio.py apps/dashboard/pyproject.toml
git commit -m "feat: generate agent portfolio snapshots"
```

### Task 5: Add the static Agent Portfolio view

**Files:**
- Create: `apps/dashboard/web/src/agentPortfolio.ts`
- Create: `apps/dashboard/web/src/agentPortfolio.test.mjs`
- Create: `apps/dashboard/web/src/components/AgentPortfolioView.tsx`
- Modify: `apps/dashboard/web/src/App.tsx`
- Modify: `apps/dashboard/web/src/styles.css`
- Create: `apps/dashboard/web/public/agent/latest.json`
- Create: `apps/dashboard/web/public/agent/history.json`
- Create: `apps/dashboard/web/public/agent/decisions.json`

**Interfaces:**
- Produce `loadAgentPortfolio(baseUrl?: string): Promise<AgentPortfolioLatest>`.
- Produce runtime guards for the contract version, finite metrics, positions, trades and decisions.
- The view must render a reviewed sample when the files exist and a clear unavailable state when they do not.

- [ ] **Step 1: Write failing parser and component tests**

```javascript
test('loads a valid agent portfolio snapshot', async () => {
  const snapshot = await parseAgentPortfolio({
    schemaVersion: 'trading_research.agent_portfolio.v1',
    generatedAt: '2026-09-01T22:00:00Z',
    asOf: '2026-09-01',
    agent: { id: 'glm-daily', provider: 'zhipu', model: 'glm-4.7-flash', promptVersion: 'v1', inputHash: 'abc' },
    portfolio: { initialEquity: 100000, equity: 100000, cash: 100000, nav: 1, totalReturn: 0, maxDrawdown: 0 },
    metrics: { totalReturn: 0, maxDrawdown: 0 },
    decision: { targetWeights: { CASH: 1 }, reasoningSummary: 'hold' },
    positions: [],
    trades: [],
    history: [],
  });
  assert.equal(snapshot.schemaVersion, 'trading_research.agent_portfolio.v1');
});

test('rejects an unsupported agent portfolio version', async () => {
  await assert.rejects(() => parseAgentPortfolio({
    schemaVersion: 'trading_research.agent_portfolio.v9',
    generatedAt: '2026-09-01T22:00:00Z',
    asOf: '2026-09-01',
    agent: { id: 'glm-daily', provider: 'zhipu', model: 'glm-4.7-flash', promptVersion: 'v1', inputHash: 'abc' },
    portfolio: { initialEquity: 100000, equity: 100000, cash: 100000, nav: 1, totalReturn: 0, maxDrawdown: 0 },
    metrics: { totalReturn: 0, maxDrawdown: 0 },
    decision: { targetWeights: { CASH: 1 }, reasoningSummary: 'hold' },
    positions: [],
    trades: [],
    history: [],
  }));
});
```

- [ ] **Step 2: Run focused frontend tests and verify failure**

Run: `pnpm --filter wu-t0-dashboard-web test -- src/agentPortfolio.test.mjs`

Expected: FAIL because the parser and view do not exist.

- [ ] **Step 3: Implement loading and rendering**

Add a compact navigation entry or section for Agent Portfolio. Use existing ECharts utilities for NAV and drawdown lines. Reuse local UI components and existing CSS tokens. Keep all labels in clear Chinese and identify the data as paper trading.

- [ ] **Step 4: Run frontend tests and build**

Run: `pnpm --filter wu-t0-dashboard-web test` and `pnpm --filter wu-t0-dashboard-web build`.

Expected: all existing and new tests pass, build exits 0.

- [ ] **Step 5: Commit the frontend**

```bash
git add apps/dashboard/web/src apps/dashboard/web/public/agent
git commit -m "feat: add agent portfolio dashboard"
```

### Task 6: Add the GitHub Actions workflow and documentation

**Files:**
- Create: `.github/workflows/agent-paper-portfolio.yml`
- Create: `docs/agent-paper-portfolio.md`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `AGENTS.md` only to document the new workflow and its manual/scheduled behavior
- Create: `scripts/test_agent_paper_workflow.py` or extend the existing workflow contract test location

**Interfaces:**
- Workflow name: `Agent paper portfolio`.
- Triggers: `workflow_dispatch` and `schedule` with one weekday run in UTC.
- Secret: `ZHIPU_API_KEY`.
- Artifact: `agent-paper-portfolio-${{ github.run_id }}` containing `latest.json`, `history.json`, `decisions.json` and a run summary.

- [ ] **Step 1: Write failing workflow contract tests**

```python
def test_agent_workflow_is_manual_and_weekday_scheduled() -> None:
    workflow_path = Path('.github/workflows/agent-paper-portfolio.yml')
    workflow = yaml.safe_load(workflow_path.read_text(encoding='utf-8'))
    assert 'workflow_dispatch' in workflow['on']
    assert workflow['on']['schedule']

def test_agent_workflow_uses_secret_and_read_only_permissions() -> None:
    workflow_path = Path('.github/workflows/agent-paper-portfolio.yml')
    text = workflow_path.read_text(encoding='utf-8')
    assert 'ZHIPU_API_KEY' in text
    assert 'contents: read' in text
    assert 'agent-portfolio' in text
```

- [ ] **Step 2: Run workflow tests and verify failure**

Run: `uv run --locked pytest scripts/test_agent_paper_workflow.py -q`

Expected: FAIL because the workflow and contract test do not exist.

- [ ] **Step 3: Implement offline-first workflow**

Use `setup-uv`, install the locked workspace, create or fetch the fixed market input, call the generator with `ZHIPU_API_KEY`, validate static assets, install pnpm dependencies, run frontend tests and build, and upload the Agent files. Keep deployment disabled by default. If the live API request fails, the job must fail without publishing a new candidate.

- [ ] **Step 4: Document setup and operational behavior**

Document API key configuration, UTC schedule, manual dispatch, paper-only semantics, model name, free-model quota limitations, artifact inspection, disabling the schedule, and the fact that no broker credentials are accepted.

- [ ] **Step 5: Run workflow contract, documentation link, and repository checks**

Run: `uv run --locked pytest scripts/test_agent_paper_workflow.py -q`, `uv run --locked ruff check .`, `uv run --locked --extra dev ty check src` from each Python package directory, `pnpm --filter wu-t0-dashboard-web test`, and `pnpm --filter wu-t0-dashboard-web build`.

- [ ] **Step 6: Commit workflow and documentation**

```bash
git add .github/workflows/agent-paper-portfolio.yml docs/agent-paper-portfolio.md README.md docs/README.md AGENTS.md scripts/test_agent_paper_workflow.py
git commit -m "feat: schedule agent paper portfolio experiment"
```

### Task 7: Full verification and PR handoff

**Files:**
- Modify: none unless verification exposes a real defect

- [ ] **Step 1: Inspect the final diff and generated files**

Run: `git status --short`, `git diff --check`, `git diff --stat`, and `git diff --name-only origin/main...HEAD`. Confirm no API key, local path, raw market data or large generated output is included.

- [ ] **Step 2: Run the full Python test suite with coverage**

Run: `uv run --locked pytest -q`.

Expected: zero failures and the output records the final test count.

- [ ] **Step 3: Run quality checks**

Run: `uv run --locked ruff check .`, the repository's configured `ty` checks for all workspace packages, `pnpm audit`, `pnpm --filter wu-t0-dashboard-web test`, and `pnpm --filter wu-t0-dashboard-web build`.

- [ ] **Step 4: Review workflow permissions and failure paths**

Read the workflow from top to bottom and confirm it cannot submit broker orders, push commits, or deploy without an explicit future change. Verify the artifact contains only paper portfolio data.

- [ ] **Step 5: Push the branch and open a draft PR**

```bash
git push -u origin feat/agent-paper-portfolio
gh pr create --draft --base main --head feat/agent-paper-portfolio \
  --title "feat: add GLM paper portfolio experiment" \
  --body-file /tmp/agent-paper-portfolio-pr.md
```

The PR body must list the data flow, secret name, paper-only boundary, tests actually run, known requirement for `ZHIPU_API_KEY`, and the fact that scheduled deployment is not enabled by default.

- [ ] **Step 6: Stop before merge until the workflow has been reviewed**

Do not merge or delete the worktree until the PR checks pass and the user approves the final scope. After approval, follow the repository's merge, branch deletion and worktree cleanup procedure.
