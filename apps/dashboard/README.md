# T+0 交易指标与图表生成脚本

基于 **Akshare + Pandas + scikit-learn + Matplotlib** 的 A 股日线/分时数据处理工具。  
脚本会为所配股票（示例：`600199 金种子酒`）自动：
- 拉取日线与分时数据
- 计算 20 日 ATR、VWAP、开盘区间 ORB
- 用 KMeans 聚类估算支撑/阻力及关键价位
- 判断交易风格（趋势/均值回归等）
- 生成图表并导出带使用说明的 Excel 仪表盘

> 仅用于研究与教育，不构成任何投资建议。

---

## 功能清单

- **数据获取**
  - 日线：`ak.stock_zh_a_hist(adjust="qfq")`
  - 分时：`ak.stock_intraday_em`
  - 交易日历：`ak.tool_trade_date_hist_sina`（失败时回退到“昨天”）
- **指标计算**
  - 20 日 ATR（真实波动幅度的简单滑动平均）
  - VWAP（分时加权成交均价）
  - ORB（09:30–09:45 开盘区间高/低）
  - KMeans 聚类中心作为关键价格，推导支撑与阻力
  - 自动交易风格判定（波动率、趋势强度、区间位置三因子）
- **可视化**
  - 价格与聚类中心线、最近关键价格
  - 成交量柱状图
  - 右上角文字框汇总关键指标
- **结果输出**
  - 图表：`stock_charts/<code>_<yyyymmdd>.png`
  - Excel：`T0交易指标_<yyyy-mm-dd>.xlsx`
    - Sheet1：`T0_Trading_Dashboard`（指标 + 使用说明）
    - Sheet2：`图表索引`（图表文件清单与路径）

---

## 环境要求

- Python >= 3.9
- 依赖库：
  ```bash
  pip install akshare pandas numpy scikit-learn matplotlib openpyxl
````

* 网络可访问 Akshare 对接的数据源
* 中文字体（用于图表中文显示）。脚本默认：

  ```python
  plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
  ```

  若在 Linux/Windows 上无该字体，可改为：

  ```python
  plt.rcParams['font.sans-serif'] = ['SimHei']  # 或 Noto Sans CJK SC
  ```

建议使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt  # 如果你把依赖写成了文件
```

---

## 快速开始

1. **克隆或放置脚本**到任意目录。
2. **安装依赖**（见上）。
3. **运行脚本**：

   ```bash
   python your_script.py
   ```
4. **查看输出**：

   * Excel：`T0交易指标_<最近交易日>.xlsx`
   * 图表目录：`stock_charts/`

运行时控制台会打印依赖版本、处理进度与异常提示。例如：

```
Akshare version: x.y.z
Pandas version: a.b.c

Processing: 金种子酒 (sh600199)...
  > 图表已保存: stock_charts/sh600199_20240930.png
✅ Excel文件 'T0交易指标_2024-09-30.xlsx' 已成功生成。
✅ 图表文件已保存到 'stock_charts' 目录
```

---

## 配置说明

脚本顶部参数区：

```python
STOCK_CONFIG = {
    "sh600199": {"name": "金种子酒"}
}

ATR_PERIOD = 20        # ATR 滚动周期
N_CLUSTERS = 5         # KMeans 聚类中心数量
CHART_OUTPUT_DIR = "stock_charts"
```

* **添加更多股票**

  ```python
  STOCK_CONFIG = {
      "sh600199": {"name": "金种子酒"},
      "sz000001": {"name": "平安银行"},
      "sh600519": {"name": "贵州茅台"},
  }
  ```

  键名格式：交易所前缀 + 6 位代码（`sh/sz` + 代码）。

* **数据区间**
  日线数据 `start_date="20240101"` 到脚本运行当天。可按需调整。

---

## 指标与逻辑

### 1) ATR（Average True Range）

* 计算方法：`TR = max(high-low, |high-前收|, |low-前收|)`，再对 TR 做 `period` 天滚动均值。
* 用途：估计日均波动，作为 VWAP 偏离阈值与风险控制的刻度。

### 2) VWAP（分时加权均价）

* 计算：`sum(price * volume) / sum(volume)`，若 volume 全为 0 则退化为分时均价。
* 用途：均值回归策略的参考线，偏离越大，次日回归概率越高（经验假设）。

### 3) ORB（Opening Range Breakout）

* 时间窗：**09:30–09:45**
* 计算：在该窗内的最高/最低价，给出突破上/下轨（脚本中各加减 0.05 元的微调）。
* 用途：开盘后若放量突破上轨则偏多，跌破下轨则偏空。

### 4) KMeans 聚类支撑/阻力

* 对收盘价聚类，排序后的最小中心为**支撑**，最大中心为**阻力**，并标记**最近关键价格**。
* 直观意义：价格分布的“驻点”与“密集带”。

### 5) 自动交易风格判定

* 指标：

  * **波动率**：`ATR20 / 最新价`
  * **趋势强度**：`|MA5 - MA20| / 最新价`
  * **区间位置**：`(最新价 - 20日最低) / (20日最高 - 20日最低)`
* 规则输出示例：

  * 高波动 + 强趋势 → `趋势跟踪 + 突破交易`
  * 高波动 + 弱趋势，中位区间 → `均值回归 + VWAP策略`
  * 低波动 + 弱趋势 → `均值回归 + 窄幅震荡策略`
    …详见源码内条件分支。

### 6) 阈值与参数

* `vwap_dev = 昨收 - 前一交易日 VWAP`
* `vwap_dev_threshold = k * ATR20`，其中 k 会随交易风格在 `0.4/0.5/0.6` 切换。
* Excel 会导出「VWAP\_DEV 触发阈值」以供盘中参考。

---

## 输出文件

### 1) 图表

* 路径：`stock_charts/<code>_<yyyymmdd>.png`
* 内容：收盘价折线、聚类中心/支撑/阻力、最近关键价、成交量、副标题为交易风格摘要。

### 2) Excel 仪表盘

* 文件名：`T0交易指标_<最近交易日>.xlsx`
* Sheet `T0_Trading_Dashboard` 字段：

  * `股票代码` / `股票名称`
  * `指标/参数`
  * `计算值`
  * `使用说明`（脚本内置字典自动映射，含核心解释与风控提示）
* Sheet `图表索引`：图表文件名与路径索引，便于定位图片。

---

## 目录结构（示例）

```
.
├── your_script.py
├── stock_charts/
│   └── sh600199_20240930.png
└── T0交易指标_2024-09-30.xlsx
```

---

## 常见问题与排错

1. **中文乱码或负号显示为方块**

   * 替换字体为 `SimHei` 或安装 `Noto Sans CJK SC`，并保留 `axes.unicode_minus=False`。

2. **Excel 正在被占用，无法写入**

   * 关闭已打开的 Excel，再运行脚本。

3. **Akshare 拉取分时失败或为空**

   * 控制台会提示 Warning。脚本将继续基于日线输出结果，但 VWAP/ORB 可能缺失。

4. **网络/数据源限流**

   * 避免高频多次运行；必要时在多只股票间设置延时（可自行在循环中 `time.sleep`）。

5. **KMeans 收敛告警或效果不理想**

   * 调整 `N_CLUSTERS`（常见 4–7），或先对价格进行标准化/分段再聚类（需要自行扩展）。

---

## 重要声明

* 本项目仅用于策略研究与学习，历史回测并不能保证未来收益。
* 任何基于本工具做出的交易决策与后果，使用者自行承担。

---

## 扩展建议

* 为多只股票批量生成结果与合并仪表盘
* 引入回测/绩效统计（胜率、盈亏比、最大回撤等）
* 以 Parquet 缓存数据，减少重复网络请求
* 增加真实成交量能量指标与盘口不平衡的实时计算
* 改造成 CLI：`python script.py --codes sh600199,sz000001 --start 20240101`

---

## 版本信息

* 依赖版本在运行时打印（Akshare、Pandas），便于定位不兼容问题。
* 建议固定依赖版本到 `requirements.txt`，例如：

  ```
  akshare==1.13.98
  pandas==2.2.2
  numpy==1.26.4
  scikit-learn==1.5.1
  matplotlib==3.8.4
  openpyxl==3.1.5
  ```

  注：版本号请根据你本地可用情况调整。
