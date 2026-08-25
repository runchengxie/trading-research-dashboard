# A1 趋势状态与牛门线的集成研究说明

## 1. 研究目的

本说明记录如何把《时序 CTA 长期均值修正版 A1》的趋势状态思想接入牛门线研究框架，同时继续遵守本仓库的原则：源材料规则、研究假设和可执行代码必须分开，不能因为某个回测结果好看就把缺失参数悄悄补成“原策略”。

本阶段要回答的问题很窄：

> 价格自身的趋势状态信息，是否能在 NML 突破信息之外提供稳定的增量过滤价值？

因此当前只研究 **long-entry regime gate**，暂不引入 A1 的震荡 RSI 反转、做空状态机或资产特定 ATR 参数。

## 2. A1 材料明确支持的内容

现有 A1 报告明确描述了以下结构：

- 在自适应窗口内联合估计 AR(1)-GARCH(1,1)；
- 把 AR(1) 截距 `c` 转为长期无条件均值 `m = c / (1 - rho)`；
- 用 `TSI_A1 = m / sigma` 表示趋势方向与单位波动下的趋势强度；
- 趋势候选还会参考 TSI 置信区间是否同号、TSI 历史分位、`rho` 的 t 统计量和波动率分位；
- 10 日窗口内至少 5 日满足候选条件后确认趋势；
- 趋势状态下顺势交易，非趋势状态下使用 RSI(14) 反转；
- 收盘后产生信号，下一交易日开盘执行。

这些信息足以说明 A1 的**架构思想**，但不足以精确复刻其趋势状态分类器。

## 3. 目前缺失、不能擅自补齐的参数

现有材料没有给出至少以下关键细节：

- “自适应窗口”的精确定义和选择规则；
- TSI 置信区间的具体估计方法；
- TSI 历史分位的阈值；
- `rho` t 统计量的门槛；
- 波动率分位的门槛；
- 多个条件之间是否全部同时满足，或存在其他组合逻辑；
- AR/GARCH 拟合失败、接近单位根或异常参数时的处理规则。

因此当前代码**不实现名为 A1 的 AR-GARCH 分类器**，也不把简单动量过滤器称为 A1 的近似复刻。

## 4. 当前 PR 的设计决定

### 4.1 独立的 `price_regime` gate

`StrategyConfig` 增加独立的价格状态过滤开关：

```text
enable_price_regime_gate
price_regime_column
minimum_price_regime_score
```

当 gate 开启时，只有价格状态分数严格高于门槛的 NML 候选才能入场。缺失值按“状态未知”处理并阻止入场，避免把没有状态信息误当成条件通过。

这个 gate 与现有 `macro_regime` / `industry_regime` 保持独立。前者来自标的自身价格序列，后者属于外部市场、行业或宏观上下文，研究归因时不应混成同一个变量。

### 4.2 先加入低复杂度 comparator

标准实验增加 `nml_simple_trend_gate`。默认价格状态分数定义为 63 个交易日的收盘收益：

```text
price_regime_t = close_t / close_(t-63) - 1
```

仅当 `price_regime_t > 0` 时允许 NML long entry。

这个 63 日动量 gate 的作用是建立一个低复杂度基准。以后真正实现 A1 状态分类器时，必须回答：

> AR-GARCH + TSI 的复杂度，是否显著优于一个简单的正收益趋势过滤器？

如果复杂模型无法稳定超过这个 comparator，就没有充分理由把额外估计误差、计算成本和参数自由度引入主策略。

### 4.3 时点约束

简单价格状态分数使用 bar `t` 收盘价，因此它只能用于 bar `t` 收盘后的 NML 信号确认，最早在 bar `t+1` 开盘成交。这与当前 NML baseline 的事件时序一致，不新增未来函数。

## 5. 当前标准实验矩阵

在相同标的、样本区间和交易成本下，固定比较：

```text
nml_baseline
nml_no_price_volume_filters
simple_20_day_breakout
nml_simple_trend_gate
buy_and_hold
```

其中 `nml_simple_trend_gate` 与 `nml_baseline` 使用相同 NML 和原有过滤器，仅额外增加价格状态 gate，因此二者差异可以相对干净地归因于趋势状态过滤。

## 6. 后续 A1 实现的进入条件

只有在 A1 缺失定义得到可靠补充后，才新增例如 `a1_trend_regime` 的独立研究模块。届时至少应输出中间量以便审计：

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

并固定比较：

```text
nml_baseline
nml_simple_trend_gate
nml_a1_trend_gate
```

A1 模块若需要 `statsmodels`、`arch` 等依赖，应作为研究依赖单独管理，并优先预计算、缓存滚动状态特征，避免每个策略变体重复拟合 GARCH。

## 7. 暂不进入本阶段的内容

以下内容应作为后续独立策略实验，而不是混进当前 NML baseline：

- 非趋势状态的 RSI 均值回归；
- TSI 负向状态的做空；
- 依据 TSI 强度动态调整仓位；
- A1 资产特定的 ATR trailing-stop 参数；
- 多资产等权组合层。

这些机制会同时改变 alpha、方向、退出、仓位和组合构造。一次性加入后，即使 Sharpe 上升也很难判断增量来自哪里。
