# R-Breaker 回测

R-Breaker 日内策略位于 `apps/dashboard/src/trading_research/strategies/rbreaker.py`，来源于历史项目 `wu-intraday-strategy`。如果当前目录已经是 `apps/dashboard/`，文中的命令可以使用相对路径 `src/trading_research/strategies/rbreaker.py`。

## 安装

回测依赖保持可选：

```bash
uv sync --extra backtest
```

## 运行

维护中的入口是包模块：

```bash
uv run python -m trading_research.strategies.rbreaker \
  --symbol 603356 \
  --data-source akshare
```

`apps/dashboard/backtest/rbreaker.py` 仍保留为迁移期兼容入口。新脚本和新文档应使用 `trading_research.strategies.rbreaker`，后续确认没有外部调用方后再单独删除兼容壳。

## AKShare

AKShare 模式不需要 token：

```bash
uv run python -m trading_research.strategies.rbreaker \
  --symbol 603356 \
  --data-source akshare
```

## Tushare

Tushare 模式需要 `TUSHARE_TOKEN`：

```bash
export TUSHARE_TOKEN=...
uv run python -m trading_research.strategies.rbreaker \
  --symbol 603356 \
  --data-source tushare \
  --in-sample-start 2025-06-01 \
  --in-sample-end 2025-06-23 \
  --out-sample-start 2025-06-24
```

PowerShell：

```powershell
$env:TUSHARE_TOKEN = "..."
```

凭据只通过环境变量提供，不写入源码或仓库文档。

## 常用参数

```text
--symbol             六位股票代码
--data-source        akshare 或 tushare
--data-folder        Tushare 分钟数据本地缓存目录
--in-sample-start    样本内起始日期
--in-sample-end      样本内结束日期
--out-sample-start   样本外起始日期
--plot               回测后绘制蜡烛图
```

## 策略流程

R-Breaker 使用前一交易日最高价、最低价和收盘价计算六个关键价格，再根据突破和反转条件产生交易信号。当前实现还包含：

- 样本内参数搜索
- 样本外验证
- Sharpe、回撤和总收益统计
- 信号准确率统计
- 收盘前强制平仓
- 可选交易记录 CSV

## 当前维护边界

R-Breaker 是从旧项目迁入的完整模块，目前仍自行维护一套 AKShare、Tushare 和本地 CSV 下载逻辑。Dashboard 主流程已经有 `trading_research.data.data_sources` 统一数据层，两套实现存在重复。

本轮维护只修复 Dashboard 主流程和基础设施，不改 R-Breaker 策略行为。后续重构更适合单独 PR，目标是让回测层只负责策略、参数优化和报告，把行情访问逐步收敛到统一数据层。

## Artifact 驱动的快照生成

### Alpaca 美股输入

可以用 Alpaca 生成一只美股的本地 R-Breaker 输入 artifact。命令只读取
`APCA_API_KEY_ID`、`APCA_API_SECRET_KEY`，也支持通过 `API_KEYS_PATH` 读取包含
`alpaca_key_id` 和 `alpaca_secret` 的 JSON 文件：

```bash
API_KEYS_PATH=/path/to/api_keys.json \
uv run --with 'alpaca-py>=0.44,<0.45' \
  python -m trading_research.scripts.build_rbreaker_alpaca_artifact \
  --symbol AAPL \
  --session-date 2025-08-22 \
  --output-root /tmp/rbreaker-aapl-input
```

producer 会请求日线和 1 分钟 bars，只保留 `America/New_York` 的 09:30–16:00
常规交易时段，默认使用 Alpaca SIP feed，自动写入前一交易日 H/L/C，并对 Parquet
文件生成 SHA-256。需要使用 IEX 时显式添加 `--feed iex`。该 artifact 适合本地探索，
暂时不会自动发布到线上。

省略 `--output-root` 时，producer 会保存到
`~/data/trading-research-dashboard/rbreaker/alpaca/<symbol>/<session-date>/`。CI 应显式
传入 runner 临时目录，避免把原始行情写入仓库工作区。

部署阶段不直接访问行情供应商。研究任务应先生成包含 `manifest.json` 和
`bars/<symbol>.parquet` 的 `trading_research.rbreaker_input.v1` artifact，再由
Dashboard 的构建任务使用锁定的 `backtest` extra 生成静态快照：

```bash
uv run --locked --extra backtest rbreaker-snapshot \
  --artifact-root /path/to/rbreaker-input-v1 \
  --output web/public/rbreaker-research.json \
  --producer-run-id research-run-123
```

生成器会校验 manifest、文件哈希、分钟线字段和前一交易日 H/L/C，并在结果通过
`research-core` 校验后原子替换输出文件。artifact 无效或回测失败时，不会覆盖已有
的 `rbreaker-research.json`。

GitHub Actions 的 `Deploy Dashboard` workflow 通过 `research_run_id` 下载同一研究任务的
`rbreaker-input-v1` artifact，再执行上述命令。需要为仓库配置只读的
`RESEARCH_ARTIFACT_TOKEN`；workflow 不会在部署 runner 上访问 AKShare 或 Tushare。
