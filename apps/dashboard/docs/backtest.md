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
