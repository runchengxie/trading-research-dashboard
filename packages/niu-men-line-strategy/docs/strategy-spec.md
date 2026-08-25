# 牛门线策略研究规格 v0.1

## 1. 目的与边界

本文件把 `restricted-strategy-notes.md` 和 `original-transcript.md` 中可验证的公式，与为了程序化研究而新增的假设明确分开。

当前目标是建立一个**可重复、无明显未来函数、可以被证伪**的研究基线。它不宣称还原了原作者完整交易系统，也不把口播中的主观判断伪装成已经验证的量化规则。

### 资料状态

已知原始材料明确给出了 NML/QRL、ATR、SMX 和两类成本线公式；但同时存在关键叙述冲突：

- 公式把 NML/QRL 放在过去 20 周期最高价之上；
- 部分口播又把 NML 描述为上涨后“回落触碰”的下方白线。

现有资料不足以证明哪一处是原作者真正意图。因此 v0.1 不修改公式符号，也不自行发明 `-ATR` 版本。

---

## 2. 已锁定的源公式

### 2.1 True Range

```text
TR_t = max(
  H_t - L_t,
  abs(H_t - C_{t-1}),
  abs(L_t - C_{t-1})
)
```

### 2.2 ATR

```text
ATR_t = SMA(TR, 14)_t
```

这里的 `MA(TR1, M)` 按简单移动平均实现。

**禁止在 baseline 中用 Wilder/RMA ATR 偷换概念。** 如果以后比较 Wilder ATR，应作为单独实验变量命名。

### 2.3 过去 20 周期前高

```text
PREV_HIGH_t = HHV(H, 20)_{t-1}
```

等价于：先对 `H` 做 20 周期滚动最高值，再整体滞后 1 个周期。

### 2.4 两条牛门线

```text
NML_t = PREV_HIGH_t + 0.5 * ATR_t
QRL_t = PREV_HIGH_t + 1.0 * ATR_t
```

### 2.5 SMX

```text
SMX_t = SMA(C, 10)_t
```

部分口播称紫线为 20 日均线，与代码冲突。baseline 以代码 `MA(C,10)` 为准。

---

## 3. 信号含义：当前 baseline 决策

### 3.1 冲突本身

若 `NML = 前20周期最高价 + 0.5ATR`，NML 数学上位于过去 20 周期最高价之上。因此它天然更像一个**向上突破阈值**，而非典型的下方跟踪支撑线。

### 3.2 v0.1 baseline

v0.1 将“第一次触碰 NML”解释为：

> 价格从 NML 下方向上突破，收盘首次站到 NML 上方。

原始入场候选：

```text
C_t >= NML_t
and
C_{t-1} < NML_{t-1}
```

这只是为了使现有 `+ATR` 公式具备一致数学含义的**研究解释**。

### 3.3 暂不实现的“回踩”解释

除非获得更可靠原始画面/公式证据，否则不实现以下猜测：

- `PREV_HIGH - 0.5ATR`
- 先突破 QRL，再回踩 NML
- NML 是其他未转录公式

这些猜测以后可以作为候选模型测试，但不得写成“原策略就是这样”。

---

## 4. ATR 时点与执行时点

### 4.1 baseline 使用当日 ATR，但只在收盘后确认信号

`ATR_t` 使用当日 `H_t/L_t/C_t`，所以在交易日结束前并不完全已知。

因此 baseline 规则为：

1. bar `t` 收盘后计算 `ATR_t`、`NML_t` 与信号；
2. bar `t` 的信号不能在 bar `t` 内成交；
3. 最早在 bar `t+1` 开盘执行。

这样不会拿当日最终高低点去假装自己在当日上午已经知道指标。

### 4.2 可选 pre-open 研究变体

代码支持 `atr_lag=1`：

```text
NML_preopen_t = PREV_HIGH_t + 0.5 * ATR_{t-1}
```

这一版本在 bar `t` 开始前已知，可用于未来研究盘中触线策略，但不属于 v0.1 默认回测。

---

## 5. “第一次触及”的 reset 规则

口播没有定义什么时候重新允许下一次“第一次触及”。为防止一天上、一天下造成机械重复交易，v0.1 增加明确状态条件：

```text
过去 reset_bars 个完整交易日的收盘价都低于各自 NML
```

默认：

```text
reset_bars = 5
```

随后当天出现向上收盘突破才认为 `armed -> entry_signal`。

这条规则属于**研究假设**，并非原材料明确参数。

未来必须对 `1 / 3 / 5 / 10 / 20` 等 reset 周期做稳健性比较，而不是只挑收益最高值。

---

## 6. 五类追高过滤器的量化定义

原材料给出的五类条件中，有些可以从单标的 OHLCV 推导，有些必须依赖外部市场/行业数据。v0.1 不会在缺数据时猜测。

### 6.1 红三兵过滤

在候选突破 bar 之前的 3 个 bar 同时满足：

```text
close > open
close 逐日上升
abs(close - open) >= 0.5 * ATR
```

则阻止当次入场。

参数：

```text
soldier_body_atr_fraction = 0.5
```

该阈值属于研究参数。

### 6.2 放量长上影过滤

候选突破 bar：

```text
upper_shadow / (high - low) >= 0.40
and
volume / previous_20_bar_mean_volume >= 1.50
```

其中：

```text
upper_shadow = high - max(open, close)
```

默认阈值 `0.40` 与 `1.50` 均属于研究参数。

### 6.3 板块退潮过滤

只有输入数据提供 `sector_close` 时才能启用。

v0.1 定义：

```text
sector_close < SMA(sector_close, 20)
and
SMA(sector_close, 20) < SMA(sector_close, 60)
```

即板块位于短期均线下方，同时短期均线低于中期均线。

没有 `sector_close` 时，该过滤器默认关闭，而不是默认“板块健康”。

### 6.4 大盘缩量 + 标的异常放量过滤

只有输入数据提供 `market_volume` 时才能启用。

默认定义：

```text
market_volume / previous_20_bar_mean_market_volume <= 0.80
and
asset_volume / previous_20_bar_mean_asset_volume >= 1.50
```

阈值属于研究参数。

### 6.5 宏观与行业逻辑过滤

OHLCV 无法自动推导“宏观逻辑成立”。v0.1 要求上游研究模块提供：

```text
macro_regime
industry_regime
```

建议统一缩放至 `[-1, 1]`。

启用 gate 后默认要求：

```text
macro_regime > 0
industry_regime > 0
```

如何生成这两个分数属于独立研究问题，不能在本策略内部用价格涨跌偷换成“宏观判断”。

---

## 7. 出场与风险管理

原材料明确说 QRL 不能机械视为最高点或固定卖点。因此 v0.1 **不使用 QRL 自动止盈**。

### 7.1 趋势退出

默认：

```text
C_t < SMX_t
```

bar `t` 收盘确认，bar `t+1` 开盘退出。

10 日均线退出属于研究 baseline，并非原材料明确的统一卖出算法。

### 7.2 初始保护止损

入场时：

```text
stop = entry_price - 2 * ATR_signal
```

默认：

```text
stop_atr_multiple = 2.0
```

止损值在入场时确定。若后续交易日低点触及止损，按止损价成交；若开盘已经跳空跌破止损，则按更差的实际开盘价成交，避免乐观填单。

### 7.3 仓位

原材料给出的追涨上限：

```text
max_position_weight = 15%
```

v0.1 同时增加组合风险预算：

```text
risk_fraction = 1% of current cash
```

头寸单位取以下三者最小：

```text
15% 仓位上限对应单位数
1% 风险预算 / 每单位止损距离
现金实际可购买单位数
```

所以 15% 是上限，而非每次固定买满 15%。

### 7.4 交易成本

回测器支持：

- `commission_bps`
- `slippage_bps`
- `lot_size`

默认成本为 0，仅用于验证逻辑。正式收益研究必须使用符合市场的成本与最小交易单位。

---

## 8. 不同资产的数据口径

所有 baseline bar 至少要求：

```text
open, high, low, close, volume
```

日期应按时间升序排列。

### 8.1 股票

成本代理优先：

```text
rolling_sum(amount, N) / rolling_sum(volume, N)
```

但必须先确认数据商：

- `amount` 是元、千元还是其他单位；
- `volume` 是股、手还是其他单位。

代码不硬编码 `/100`，使用显式 `amount_scale` 调整。

### 8.2 ETF

和股票相同，优先使用成交额 / 成交量，但仍需确认成交量单位及复权方式。

复权 OHLC 与原始成交额/成交量混用可能导致成本代理失真，数据管线需要统一口径。

### 8.3 指数

若指数没有真正可交易成交额，采用原材料中的代理：

```text
rolling_sum(close * volume, N) / rolling_sum(volume, N)
```

它只是“按每日收盘点位加权的价格代理”，不应称为严格 VWAP。

### 8.4 期货 / 商品

默认也只能使用：

```text
rolling_sum(close * volume, N) / rolling_sum(volume, N)
```

若要使用成交额，需要额外处理合约乘数、报价单位、主力连续换月和复权逻辑。

正式期货回测还必须定义：

- 合约选择；
- 换月；
- 手数；
- 保证金；
- 夜盘交易日归属；
- 涨跌停和流动性约束。

这些不属于 v0.1 单资产日线 baseline。

---

## 9. 事件驱动回测时序

默认循环：

```text
bar t 开盘
  -> 执行 t-1 收盘产生的退出指令
  -> 执行 t-1 收盘产生的入场指令
  -> 检查已知保护止损是否盘中触发
bar t 收盘
  -> mark-to-market
  -> 计算 t 收盘信号
  -> 生成 t+1 待执行指令
```

关键原则：

- 当日收盘才能知道的条件绝不在当日更早价格成交；
- 止损必须用当时已经存在的止损位；
- 跳空穿越止损不能按理想止损价成交；
- 数据最后仍有持仓时按最后收盘价结算，并标记 `end_of_data`。

---

## 10. 绩效指标

回测器当前输出：

- final equity
- total return
- annualized return
- Sharpe ratio
- maximum drawdown
- trade count
- win rate
- profit factor

这些指标只有在使用真实历史数据、正确交易成本、合理样本切分后才有研究意义。

单次样本的高 Sharpe 不能证明策略有效。

---

## 11. 第四阶段实验设计

获得历史数据后，不直接做全参数穷举并挑最高收益。建议按以下顺序：

### 11.1 先验证公式解释

至少比较：

1. `+ATR` close-confirmed breakout baseline；
2. `+ATR` pre-open (`ATR_{t-1}`) intraday-touch 变体；
3. 只有得到新证据后，才加入“回踩型”候选公式。

### 11.2 再做参数稳健性

建议网格仅用于稳定性检查：

```text
high_lookback: 10, 20, 40
atr_period: 10, 14, 20
nml_multiple: 0.25, 0.5, 0.75, 1.0
reset_bars: 1, 3, 5, 10, 20
stop_atr_multiple: 1.0, 1.5, 2.0, 3.0
```

关注参数邻域是否稳定，而非某一个点是否异常漂亮。

### 11.3 样本切分

至少需要：

- in-sample / out-of-sample；
- 不同牛熊阶段；
- 多标的横截面；
- walk-forward 或滚动验证。

### 11.4 对照组

必须比较：

- buy-and-hold；
- 简单 20 日突破；
- 简单 10/20 日趋势策略；
- 去掉五类过滤器的 NML；
- 逐个加入过滤器后的增量贡献。

如果复杂规则没有稳定超过简单突破基线，就没有充分理由保留复杂度。

---

## 12. 当前未解决问题

以下事项仍需要额外证据或数据，不能由代码替用户决定：

1. 原视频中白线在具体案例时究竟位于价格上方还是下方；
2. `+0.5ATR` 是否始终正确，还是存在另一版本公式；
3. “回落摸线”究竟指价格回落，还是图表视觉/口播表达不准确；
4. 口播紫线 20 日均线与代码 10 日均线的真实意图；
5. 原材料提到的 4 个宏观节点中缺失的两个；
6. 股票/ETF/指数/期货数据供应商的成交量、成交额单位；
7. 宏观与行业 regime 分数的独立构建方法。

在这些问题解决前，任何回测结果都应标记为“当前研究解释的结果”，不能写成“原牛门线策略的真实历史表现”。
