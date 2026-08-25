# Niu Men Line Strategy Research

这是牛门线策略的研究型实现。仓库将原始资料、研究假设和可执行代码分开管理，先验证规则与交易时点，再评估历史表现。

## 当前状态

已实现：

- 原始 NML / QRL / SMX 公式；
- `MA(TR, 14)` 简单 ATR；
- 股票/ETF 与指数/期货的滚动成本代理；
- 收盘确认、下一交易日开盘执行的 NML 突破基线；
- “第一次触及” reset 状态；
- 红三兵、放量长上影过滤器；
- 可选板块退潮、大盘量能背离、宏观/行业 regime gate；
- 单资产事件驱动回测，支持跳空止损与涨跌停开盘导致的成交延后；
- 15% 仓位上限 + 1% 风险预算 + 2ATR 保护止损；
- 跳空止损处理；
- 收益率、Sharpe、最大回撤、胜率、盈亏比等指标；
- 月度点时股票池、行业历史归属、宽基市场量能上下文和滚动样本外切分工具。

策略定义、来源冲突和研究假设见 [`docs/strategy-spec.md`](docs/strategy-spec.md)。

## 重要限制

原材料中的公式为：

```text
NML = REF(HHV(H,20),1) + 0.5 * ATR
QRL = REF(HHV(H,20),1) + 1.0 * ATR
```

这使 NML 位于此前 20 周期最高价之上，因此当前代码把它作为**向上突破阈值**。部分口播又描述为上涨后的“回落触线”，两者存在尚未解决的冲突。

当前基线保留 `+ATR` 公式，并将结果称为研究解释。原作者完整交易系统仍需更多材料验证。

## 安装与测试

```bash
uv run --with pytest pytest
```

## CSV 回测

CSV 至少包含：

```text
date,open,high,low,close,volume
```

运行：

```bash
uv run niu-men-backtest data.csv \
  --commission-bps 5 \
  --slippage-bps 5 \
  --lot-size 100
```

输出 JSON 包括策略参数、回测参数、绩效指标和逐笔交易。

如果只想验证核心突破信号、暂时关闭两类 OHLCV 过滤器：

```bash
uv run niu-men-backtest data.csv --disable-price-volume-filters
```

## 可选上下文列

以下过滤器默认关闭，因为单标的 OHLCV 无法可靠推出这些信息：

- `sector_close`：用于板块退潮过滤；
- `market_volume`：用于大盘缩量与标的异常放量过滤；
- `macro_regime`：建议范围 `[-1, 1]`；
- `industry_regime`：建议范围 `[-1, 1]`。

启用对应 gate 时，输入数据缺少所需列会直接报错。

## 本地 A 股数据与固定对照实验

已支持本机 market-data-platform 的 `daily-clean` Parquet 数据。原始数据留在
数据平台目录中。默认使用 `adj_open/adj_high/adj_low/adj_close`，以减少除权除息
对信号的干扰。`vol`（手）和 `amount`（千元）会映射为 `volume` 与 `amount`。如
使用成本代理，当前 TuShare 口径应显式传入 `amount_scale=10`。
完整字段映射、复权口径与当前数据限制见 [`docs/data-contract.md`](docs/data-contract.md)。

```bash
uv run niu-men-experiments 600519.SH \
  --daily-clean-root ~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest \
  --commission-bps 5 --slippage-bps 5 --lot-size 100
```

命令在同一标的、同一交易成本和相同样本区间下输出四项预先固定的比较：
`nml_baseline`、去 OHLCV 过滤的 NML、普通 20 日突破和 buy-and-hold。它不是
参数寻优。行业、市场和 regime gate 需要输入相应的上下文字段。
若要将 NML/QRL 的 ATR 组成部分改为前一日已知的值，可在任一 CLI 中添加
`--atr-lag 1`。该变体仍在收盘确认信号，并于下一交易日开盘执行。

## 点时研究与滚动样本外验证

`context.py` 提供月度点时股票池和行业历史归属工具。月末快照从下一交易日生效。
`walk_forward.py` 提供冻结参数的滚动样本外切分工具。当前市场量能可使用 CSI800
等宽基指数成交量代理。行业日线尚未接入，因此板块退潮 gate 继续要求上游提供
`sector_close`。

涨跌停价会按复权比例转换到回测价格口径。若信号执行日开盘触及涨停，买入指令取消。
若开盘触及跌停，卖出与保护止损会延后到下一次可在开盘成交的交易日。日线数据无法
表达排队顺序和实际成交量，这项处理属于保守近似。

## 项目结构

```text
docs/
  original-transcript.md
  restricted-strategy-notes.md
  strategy-spec.md
  data-contract.md
src/niu_men_line_strategy/
  indicators.py
  signals.py
  backtest.py
  cli.py
  context.py
  walk_forward.py
tests/
AGENTS.md
pyproject.toml
```

## 研究顺序

1. 核对原始视频与公式，处理 `+ATR` 和回踩叙述的冲突。
2. 使用真实历史数据建立基线。
3. 进行滚动样本外、跨市场和参数邻域稳健性测试。
4. 与普通 20 日突破、均线趋势和 buy-and-hold 对照。
5. 仅保留能稳定提供增量价值的复杂过滤器。

课程转录带有仅供内部教学、禁止传播等原始声明。仓库应继续保持 private。公开代码时应将研究实现与受限制材料分开。
