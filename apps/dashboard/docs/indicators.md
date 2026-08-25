# 指标与逻辑

这里说明每个指标怎么算、怎么用。数据获取部分的接口名在代码里都有，如需了解可看 `astock_tech.py` 顶部。

## 数据获取

数据获取统一收口在 `src/trading_research/data/data_sources.py`，按
`akshare -> tushare -> 本地缓存` 的顺序兜底；根目录的 `data_sources.py` 仅用于兼容旧命令。

* 日线数据：优先 `ak.stock_zh_a_hist(adjust="qfq")`，失败则 `tushare.daily(adj="qfq")`
* 分时数据：优先 `ak.stock_intraday_em`，失败则 `tushare.stk_mins(freq="1min")`
* 交易日历：优先 `ak.tool_trade_date_hist_sina`，失败则 `tushare.trade_cal`，再失败回退到昨天
* tushare 使用双 token：`TUSHARE_TOKEN_2`（主力）与 `TUSHARE_TOKEN`（兜底），按顺序尝试；当日额度耗尽会切换到下一个 token
* 三个源全部失败时，复用上次成功抓取的 `data/raw/` 快照，保证报告仍能生成

## 1. ATR，Average True Range

* 计算方式为 `TR = max(high-low, |high-前收|, |low-前收|)`，再对 TR 做 `period` 天滚动均值
* 用途是估计日均波动空间，作为 VWAP 偏离阈值与风险控制的刻度

## 2. VWAP，分时加权均价

* 计算方式为 `sum(price * volume) / sum(volume)`，成交量全为 0 时退化为分时均价
* 用途是作为均值回归策略的参考线，偏离越大，次日回归概率越高，这是经验假设

## 3. ORB，Opening Range Breakout

* 时间窗为 09:30 至 09:45
* 取该时段内的最高价与最低价作为突破上下轨，脚本中再各加减 0.05 元作微调
* 开盘后若放量突破上轨则偏多，跌破下轨则偏空

## 4. KMeans 聚类支撑与阻力

* 对收盘价聚类，排序后的最小中心为支撑，最大中心为阻力，并标记距离最新价最近的关键价格
* 直观理解是价格分布中的密集带，即驻点

## 5. 自动交易风格判定

* 波动率为 `ATR20 / 最新价`
* 趋势强度为 `|MA5 - MA20| / 最新价`
* 区间位置为 `(最新价 - 20日最低) / (20日最高 - 20日最低)`

规则输出示例：

* 高波动且强趋势，对应 `趋势跟踪 + 突破交易`
* 高波动但弱趋势，且价格位于区间中位，对应 `均值回归 + VWAP策略`
* 低波动且弱趋势，对应 `均值回归 + 窄幅震荡策略`

完整的分支判断见源码。

## 6. 阈值与参数

* `vwap_dev = 昨收 - 前一交易日 VWAP`
* `vwap_dev_threshold = k * ATR20`，其中 k 随交易风格在 0.4、0.5、0.6 之间切换，也可以按股票覆盖
* Excel 会导出 `VWAP_DEV 触发阈值` 供盘中参考
