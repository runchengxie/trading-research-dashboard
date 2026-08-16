# T+0 交易指标与图表生成

基于 Akshare、Pandas、scikit-learn 和 Matplotlib 的 A 股日线与分时数据处理工具。脚本会为配置中的股票自动拉取数据、计算 T+0 交易指标、生成图表，并导出一份带使用说明的 Excel 仪表盘。

## 功能来源与迁移

本项目是 T+0 交易体系的基准项目，整合了以下兄弟项目的功能。

| 来源项目 | 迁移内容 | 落点 |
| --- | --- | --- |
| `wu-t0-trading-assitant` | 按股票覆盖 `vwap_dev_k` 与 `roll_ratio` 的 `STOCK_CONFIG` 配置机制 | `astock_tech.py` |
| `wu-intraday-strategy` | R-Breaker 日内策略回测模块，含 akshare 与 tushare 双数据源、参数优化、信号准确率评分、样本内外测试 | `backtest/rbreaker.py`，CLI 命令为 `rbreaker` |

原项目均保留并标记为已转移，不再单独迭代。回测模块依赖为可选，安装方式见下方「回测模块」章节。

## 功能清单

* 数据获取
  * 日线数据 `ak.stock_zh_a_hist(adjust="qfq")`
  * 分时数据 `ak.stock_intraday_em`
  * 交易日历 `ak.tool_trade_date_hist_sina`，失败时回退到昨天
* 指标计算
  * 20 日 ATR，即真实波动幅度的简单滑动平均
  * VWAP，即分时加权成交均价
  * ORB，即 09:30 至 09:45 的开盘区间高低
  * KMeans 聚类中心作为关键价格，并推导支撑与阻力
  * 自动交易风格判定，综合波动率、趋势强度、区间位置三个因子
* 可视化
  * 收盘价与聚类中心线，标注最近关键价格
  * 成交量柱状图
  * 图表右上角文字框汇总关键指标
* 结果输出
  * 图表 `out/charts/<code>_<yyyymmdd>.png`
  * Excel `out/indicators/T0交易指标_<yyyy-mm-dd>.xlsx`
    * Sheet `T0_Trading_Dashboard`，含指标和使用说明
    * Sheet `图表索引`，列出图表文件清单与路径

## 环境要求

* Python 3.9 及以上
* 依赖库在 `pyproject.toml` 中声明，建议用 uv 管理

    ```bash
    uv sync
    ```

* 网络可访问 Akshare 对接的数据源
* 中文字体，用于图表中文显示。脚本默认按顺序尝试 `Noto Sans CJK SC`、`SimHei`、`DejaVu Sans`，在 Linux 或 Windows 上可改为已有的中文字体

    ```python
    plt.rcParams['font.sans-serif'] = ['SimHei']
    ```

## 快速开始

1. 安装依赖，见「环境要求」。
2. 运行脚本：

    ```bash
    uv run python astock_tech.py
    ```

    指定股票或输出目录：

    ```bash
    uv run python astock_tech.py --codes sh600199,sz000001 --output-root out
    ```

3. 查看输出：
   * Excel 仪表盘在 `out/indicators/` 目录
   * 图表在 `out/charts/` 目录

## 静态 HTML 报告

加 `--report` 参数会额外生成一份自包含的静态 HTML 报告，把指标表格和图表渲染成一个页面，适合发布到 GitHub Pages：

```bash
uv run python astock_tech.py --report
```

报告输出到 `out/site/` 目录，其中的 `index.html` 是入口，图表复制进同目录的 `charts/` 下，整体可直接部署。也可以用 `--report-output` 指定输出目录。

仓库里附带一个 GitHub Actions 定时任务（`.github/workflows/report.yml`），每个工作日开盘前自动跑一次并把报告发布到 gh-pages。akshare 从 CI 的海外环境访问可能不稳定，生成步骤失败时不会覆盖已有站点。

运行时控制台会打印依赖版本、处理进度与异常提示，例如：

```text
Akshare version: x.y.z
Pandas version: a.b.c

Processing: 金种子酒 (sh600199)...
  > 图表已保存: out/charts/sh600199_20240930.png
Excel 文件已生成: out/indicators/T0交易指标_2024-09-30.xlsx
图表文件已保存到 out/charts 目录
```

## 回测模块

从 `wu-intraday-strategy` 迁移整合的 R-Breaker 日内策略回测模块，位于 `backtest/rbreaker.py`。依赖为可选，需要时单独安装：

```bash
uv sync --extra backtest
```

安装后使用 CLI 命令 `rbreaker` 或直接运行脚本：

```bash
rbreaker --symbol 603356 --data-source akshare
```

tushare 数据源需要 token，通过环境变量 `TUSHARE_TOKEN` 提供，不要写入代码或提交到仓库：

```bash
# Windows PowerShell
$env:TUSHARE_TOKEN = "你的token"
rbreaker --symbol 603356 --data-source tushare \
    --in-sample-start 2025-06-01 --in-sample-end 2025-06-23 --out-sample-start 2025-06-24
```

其他常用选项：

* `--data-folder`，tushare 本地缓存目录
* `--plot`，回测结束后绘制蜡烛图

## 配置说明

脚本顶部的参数区：

```python
STOCK_CONFIG = {
    "sh600199": {"name": "金种子酒"}
}

ATR_PERIOD = 20        # ATR 滚动周期
N_CLUSTERS = 5         # KMeans 聚类中心数量
OUTPUT_ROOT = "out"    # 输出根目录，图表和 Excel 分别写入其下的 charts 和 indicators
```

添加更多股票，键名格式为交易所前缀加 6 位代码：

```python
STOCK_CONFIG = {
    "sh600199": {"name": "金种子酒"},
    "sz000001": {"name": "平安银行"},
    "sh600519": {"name": "贵州茅台"},
}
```

每个股票配置里可以带 `vwap_dev_k` 和 `roll_ratio` 字段，用于覆盖自动推导的 ATR 系数和仓位滚动比例，这也是从 `wu-t0-trading-assitant` 迁移过来的机制。

数据区间默认为 `20240101` 到脚本运行当天，可按需调整日线数据的 `start_date`。

## 指标与逻辑

### 1. ATR，Average True Range

* 计算方式为 `TR = max(high-low, |high-前收|, |low-前收|)`，再对 TR 做 `period` 天滚动均值。
* 用途是估计日均波动空间，作为 VWAP 偏离阈值与风险控制的刻度。

### 2. VWAP，分时加权均价

* 计算方式为 `sum(price * volume) / sum(volume)`，成交量全为 0 时退化为分时均价。
* 用途是作为均值回归策略的参考线，偏离越大，次日回归概率越高，这是经验假设。

### 3. ORB，Opening Range Breakout

* 时间窗为 09:30 至 09:45。
* 取该时段内的最高价与最低价作为突破上下轨，脚本中再各加减 0.05 元作微调。
* 开盘后若放量突破上轨则偏多，跌破下轨则偏空。

### 4. KMeans 聚类支撑与阻力

* 对收盘价聚类，排序后的最小中心为支撑，最大中心为阻力，并标记距离最新价最近的关键价格。
* 直观理解是价格分布中的密集带，即驻点。

### 5. 自动交易风格判定

* 波动率为 `ATR20 / 最新价`
* 趋势强度为 `|MA5 - MA20| / 最新价`
* 区间位置为 `(最新价 - 20日最低) / (20日最高 - 20日最低)`

规则输出示例：

* 高波动且强趋势，对应 `趋势跟踪 + 突破交易`
* 高波动但弱趋势，且价格位于区间中位，对应 `均值回归 + VWAP策略`
* 低波动且弱趋势，对应 `均值回归 + 窄幅震荡策略`

完整的分支判断见源码。

### 6. 阈值与参数

* `vwap_dev = 昨收 - 前一交易日 VWAP`
* `vwap_dev_threshold = k * ATR20`，其中 k 随交易风格在 0.4、0.5、0.6 之间切换，也可以按股票覆盖
* Excel 会导出 `VWAP_DEV 触发阈值` 供盘中参考

## 输出文件

### 1. 图表

* 路径为 `out/charts/<code>_<yyyymmdd>.png`
* 内容包含收盘价折线、聚类中心、支撑阻力、最近关键价、成交量，副标题为交易风格摘要

### 2. Excel 仪表盘

* 文件名为 `out/indicators/T0交易指标_<最近交易日>.xlsx`
* Sheet `T0_Trading_Dashboard` 字段：
  * `股票代码` 和 `股票名称`
  * `指标/参数`
  * `计算值`
  * `使用说明`，由脚本内置字典自动映射，包含核心解释与风控提示
* Sheet `图表索引`，列出图表文件名与路径

## 目录结构

```text
.
├── astock_tech.py
├── report.py
├── backtest/
│   └── rbreaker.py
├── tests/
├── .github/
│   └── workflows/
│       └── report.yml
├── out/
│   ├── charts/
│   ├── indicators/
│   └── site/
└── pyproject.toml
```

## 测试

项目使用 pytest，运行方式为：

```bash
uv run pytest
```

测试覆盖脚本与回测模块的导入和 CLI 帮助信息。

## 常见问题与排错

1. 中文乱码或负号显示为方块
   * 更换字体为已有的中文字体，例如 `SimHei`，并保留 `axes.unicode_minus=False`。
2. Excel 文件被占用，无法写入
   * 关闭已打开的 Excel 再运行脚本。
3. Akshare 拉取分时失败或为空
   * 控制台会给出提示，脚本继续基于日线输出结果，但 VWAP 和 ORB 可能缺失。
4. 网络或数据源限流
   * 避免高频多次运行，必要时在多只股票间增加延时。
5. KMeans 收敛告警或效果不理想
   * 调整 `N_CLUSTERS`，常见取 4 到 7，或先对价格做标准化再聚类，这需要自行扩展。

## 重要声明

* 本项目仅用于策略研究与学习，历史回测不能保证未来收益。
* 任何基于本工具做出的交易决策与后果，由使用者自行承担。

## 扩展建议

* 为多只股票批量生成结果并合并仪表盘
* 引入回测与绩效统计，例如胜率、盈亏比、最大回撤
* 用 Parquet 缓存数据，减少重复网络请求
* 增加真实成交量能量指标与盘口不平衡的实时计算
* 更多 CLI 参数，例如 `--start` 控制数据起始日期

## 版本信息

* 运行时会打印 Akshare 与 Pandas 的版本，便于定位兼容问题。
* 依赖版本在 `pyproject.toml` 中声明，`uv.lock` 锁定精确版本。
