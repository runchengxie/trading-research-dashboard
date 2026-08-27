# A1 趋势状态与牛门线的集成研究说明

## 1. 研究目的

本说明记录如何把《时序 CTA 长期均值修正版 A1》的趋势状态思想接入牛门线研究框架。源材料规则、研究假设和可执行代码分别记录，缺失参数也单独列出。

当前问题是：价格自身的趋势状态信息，能否在 NML 突破信息之外提供稳定的增量过滤价值？因此本阶段只研究多头入场的 `price_regime` gate，暂不加入 A1 的 RSI 反转、做空状态机或资产专用 ATR 参数。

## 2. A1 材料明确支持的内容

现有 A1 报告描述了以下结构：

- 在自适应窗口内联合估计 AR(1)-GARCH(1,1)
- 把 AR(1) 截距 `c` 转为长期无条件均值 `m = c / (1 - rho)`
- 用 `TSI_A1 = m / sigma` 表示趋势方向与单位波动下的趋势强度
- 参考 TSI 置信区间是否同号、TSI 历史分位、`rho` 的 t 统计量和波动率分位确认趋势
- 10 日窗口内至少 5 日满足候选条件后确认趋势
- 趋势状态下顺势交易，非趋势状态下使用 RSI(14) 反转
- 收盘后产生信号，下一交易日开盘执行

这些内容说明了 A1 的架构思路，但不足以精确复刻趋势状态分类器。

## 3. 尚未定义的参数

现有材料没有给出以下细节：

- 自适应窗口的定义和选择规则
- TSI 置信区间的估计方法
- TSI 历史分位阈值
- `rho` t 统计量门槛
- 波动率分位门槛
- 各条件之间是全部满足，还是采用其他组合逻辑
- AR/GARCH 拟合失败、接近单位根或参数异常时的处理规则

当前代码不实现名为 A1 的 AR-GARCH 分类器，也不把简单动量过滤器标成 A1 复刻。

## 4. 当前研究实现

### 4.1 独立的 `price_regime` gate

`StrategyConfig` 提供以下开关：

```text
enable_price_regime_gate
price_regime_column
minimum_price_regime_score
```

启用 gate 后，只有价格状态分数高于门槛的 NML 候选才能入场。缺失值表示状态未知，直接阻止入场。

这个 gate 与 `macro_regime`、`industry_regime` 保持独立。前者来自标的自身价格序列，后两者属于外部市场、行业或宏观上下文，研究归因时应分开统计。

### 4.2 低复杂度 comparator

标准实验包含 `nml_simple_trend_gate`。默认价格状态分数为 63 个交易日的收盘收益：

```text
price_regime_t = close_t / close_(t-63) - 1
```

只有 `price_regime_t > 0` 时才允许 NML 多头入场。它用于建立低复杂度基准，后续若实现 A1 状态分类器，需要比较两者的增量价值。

### 4.3 时点约束

价格状态分数使用 bar `t` 的收盘价，只能用于 bar `t` 收盘后的 NML 信号确认，最早在 bar `t+1` 开盘成交。该时序与 NML baseline 一致。

## 5. 实验矩阵

在相同标的、样本区间和交易成本下，固定比较：

```text
nml_baseline
nml_no_price_volume_filters
simple_20_day_breakout
nml_simple_trend_gate
buy_and_hold
```

点时全市场滚动样本外脚本还包含 `nml_sector_retreat`，完整矩阵为：

```text
nml_baseline
nml_no_price_volume_filters
simple_20_day_breakout
nml_simple_trend_gate
nml_sector_retreat
buy_and_hold
```

此前逐标的结果显示，`nml_simple_trend_gate` 减少入场次数并改善部分回撤指标，但 Sharpe 没有稳定提升。这里的中位数是股票与窗口层面的描述统计，不能直接当作可交易组合收益。

组合级结果属于外部研究产物，不随当前代码包提交。

## 6. A1 实现的进入条件

只有在缺失定义得到可靠补充后，才新增 `a1_trend_regime` 独立研究模块。至少应输出以下中间量，方便审计：

```text
rho
intercept
long_run_mean
conditional_volatility
tsi_a1
trend_candidate
trend_confirmed
trend_direction
```

研究中应固定比较：

```text
nml_baseline
nml_simple_trend_gate
nml_a1_trend_gate
```

如果引入 `statsmodels`、`arch` 等依赖，应放入独立研究依赖，并优先预计算和缓存滚动状态特征，避免每个策略变体重复拟合 GARCH。

## 7. 暂不纳入本阶段的内容

以下内容留作独立策略实验：

- 非趋势状态的 RSI 均值回归
- TSI 负向状态的做空
- 按 TSI 强度动态调整仓位
- A1 资产专用的 ATR trailing stop 参数
- 多资产等权组合层

这些机制会同时改变 alpha、方向、退出、仓位和组合构造。一次性加入后，即使 Sharpe 上升，也很难确认增量来自哪一部分。
