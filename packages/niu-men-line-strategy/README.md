# Niu Men Line Strategy Research

这是“牛门线”策略的研究型实现。仓库把原始资料、研究假设和可执行代码分开管理，目标是先保证规则可复现、时点无明显未来函数，再讨论收益表现。

## 当前状态

已实现：

- 原始 NML / QRL / SMX 公式；
- `MA(TR, 14)` 简单 ATR；
- 股票/ETF 与指数/期货的滚动成本代理；
- close-confirmed NML 突破 baseline；
- “第一次触及” reset 状态；
- 红三兵、放量长上影过滤器；
- 可选板块退潮、大盘量能背离、宏观/行业 regime gate；
- 下一交易日开盘执行的单资产事件驱动回测；
- 15% 仓位上限 + 1% 风险预算 + 2ATR 保护止损；
- 跳空止损处理；
- Return、Sharpe、Max Drawdown、Win Rate、Profit Factor 等指标。

策略定义、来源冲突和研究假设见 [`docs/strategy-spec.md`](docs/strategy-spec.md)。

## 重要限制

原材料中的公式为：

```text
NML = REF(HHV(H,20),1) + 0.5 * ATR
QRL = REF(HHV(H,20),1) + 1.0 * ATR
```

这使 NML 位于此前 20 周期最高价之上，因此当前代码把它作为**向上突破阈值**。部分口播又描述为上涨后的“回落触线”，两者存在尚未解决的冲突。

当前实现不擅自把 `+ATR` 改成 `-ATR`，也不宣称已经还原原作者完整策略。

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

启用对应 gate 但缺少列时，代码会直接报错，避免把“没有数据”误写成“条件通过”。

## 本地 A 股数据与固定对照实验

已支持本机 market-data-platform 的 `daily-clean` Parquet 数据；不复制原始
数据进仓库。默认使用 `adj_open/adj_high/adj_low/adj_close`，以避免除权除息
造成假突破。`vol`（手）和 `amount`（千元）会保留为 `volume` 与 `amount`；如
使用成本代理，当前 TuShare 口径应显式传入 `amount_scale=10`。
完整字段映射、复权口径与当前数据限制见 [`docs/data-contract.md`](docs/data-contract.md)。

```bash
uv run niu-men-experiments 600519.SH \
  --daily-clean-root ~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest \
  --commission-bps 5 --slippage-bps 5 --lot-size 100
```

命令在同一标的、同一交易成本和相同样本区间下输出四项预先固定的比较：
`nml_baseline`、去 OHLCV 过滤的 NML、普通 20 日突破和 buy-and-hold。它不是
参数寻优；行业/市场/regime gate 仍须在输入数据具备相应上下文字段后单独启用。
若要将 NML/QRL 的 ATR 组成部分改为前一日已知的值，可在任一 CLI 中添加
`--atr-lag 1`；这仍是收盘确认、下一开盘执行的变体，不是未经实现的盘中触线策略。

## 项目结构

```text
docs/
  original-transcript.md
  restricted-strategy-notes.md
  strategy-spec.md
src/niu_men_line_strategy/
  indicators.py
  signals.py
  backtest.py
  cli.py
tests/
AGENTS.md
pyproject.toml
```

## 研究顺序

1. 先核对原始视频/公式，处理 `+ATR` 与“回踩”叙述冲突；
2. 用真实历史数据建立 baseline；
3. 进行 out-of-sample、跨市场和参数邻域稳健性测试；
4. 与简单 20 日突破、均线趋势和 buy-and-hold 对照；
5. 只有复杂过滤器稳定带来增量价值时才保留。

仓库中的课程转录包含“仅供内部教学、禁止传播”等原始声明，因此仓库应继续保持 private，公开代码时应把研究实现与受限制原始材料分离。
