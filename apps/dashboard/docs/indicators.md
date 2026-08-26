# 指标与逻辑

指标计算主要位于 `src/trading_research/dashboard/astock_tech.py`。行情获取统一由 `src/trading_research/data/data_sources.py` 负责，股票、ETF 和不同供应商的具体回退顺序见 [数据源与 ETF 接入](data-sources.md)。

## ATR

ATR 使用 True Range：

```text
TR = max(
  high - low,
  |high - 前收|,
  |low - 前收|
)
```

随后对 TR 计算 `period` 日滚动均值。当前默认周期为 20 日。

主要用途：

- 衡量近期日均波动空间
- 参与 VWAP 偏离阈值计算
- 给盘中风险控制提供统一的波动刻度

## VWAP

分时 VWAP：

```text
sum(price * volume) / sum(volume)
```

当分时成交量总和为 0 时，代码退化为分时价格的简单均值。

Dashboard 当前使用上一交易日的分时数据计算 VWAP。没有可用分时数据时：

```text
vwap = null
vwapDev = null
```

`vwapDevThreshold` 仍可以由 ATR 和交易风格计算，因为它代表触发尺度，并不依赖实际 VWAP 数值。

关于价格偏离后是否更容易均值回归，只能视为策略假设，需要结合独立回测验证，不能从这个指标本身推出收益结论。

## ORB

ORB 使用 09:30 至 09:45 的开盘区间：

```text
ORB high = 区间最高价
ORB low  = 区间最低价
```

当前 Dashboard 输出时对上下轨各做 0.05 元调整：

```text
突破上轨 = ORB high + 0.05
突破下轨 = ORB low - 0.05
```

缺少分时数据时 ORB 为空。

## KMeans 支撑与阻力

代码对历史收盘价执行 KMeans 聚类，默认聚类数量为 5。

排序后的聚类中心用于生成：

- 最低中心：聚类支撑位
- 最高中心：聚类阻力位
- 距离最新收盘价最近的中心：最近关键价格
- 其他中心：中间价格结构

这些位置反映历史价格分布中的聚集区域，不代表市场一定会在对应价格反转。

## 自动交易风格

风格判断使用三个量：

```text
波动率 = ATR20 / 最新价
趋势强度 = |MA5 - MA20| / 最新价
区间位置 = (最新价 - 20 日最低) / (20 日最高 - 20 日最低)
```

当前代码可能输出以下机器字符串：

```text
Trend-following + Breakout
Mean reversion + VWAP
Breakout + Momentum
Trend-following + Grid
Mean reversion + Range
```

这些字符串也会写入前端 `tradingStyle`，因此修改名称时需要同步考虑数据契约和展示层。

## VWAP 偏离阈值

实际偏离：

```text
vwap_dev = 昨收 - 上一交易日 VWAP
```

阈值：

```text
vwap_dev_threshold = vwap_dev_k * ATR20
```

当前自动系数：

| 风格 | `vwap_dev_k` |
| --- | ---: |
| `Mean reversion + VWAP` | 0.4 |
| `Trend-following + Breakout` | 0.6 |
| 其他当前风格 | 0.5 |

单证券可以在 `STOCK_CONFIG` 中用 `vwap_dev_k` 覆盖自动结果。

这部分逻辑以前通过中文子串匹配英文风格名称，导致自动分支无法命中。维护版本改为显式风格映射，并增加回归测试，避免文案语言再次影响参数选择。
