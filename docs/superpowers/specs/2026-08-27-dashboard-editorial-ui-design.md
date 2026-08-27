# Dashboard Editorial Research UI 设计

## 状态

本设计已在对话中确认。参考图仅作为 UI 设计语言来源；Dashboard 的业务内容、行情字段、策略指标和信息架构继续由本项目自身的数据与功能决定。

## 目标

将 `apps/dashboard/web` 的视觉语言从偏 SaaS 的圆角卡片工作台，收敛为更适合金融研究的 editorial / internal-audit 风格，同时保留现有三个一级区域：

- 盘前概览
- 日内工作台
- 策略研究

功能、数据契约和策略计算不因为换肤改变。

## 视觉原则

### 1. 页面基底

浅色模式使用略暖的研究纸张底色，并允许极低对比度的辅助网格。页面主体依靠留白和分隔线组织，不依赖大量悬浮白卡。

深色模式继续保留，采用同一层级系统的 dark research terminal 表达，不做机械反色。

### 2. 层级

使用稳定的四层文字层级：

1. 英文或短标签 kicker；
2. 页面 / 区域主标题；
3. 正文与指标名；
4. metadata、来源、时间和辅助说明。

数字、证券代码、日期和指标值优先使用 tabular numerals。

### 3. 颜色

- 蓝色：主结构、当前选择和交互强调；
- 红 / 绿：继续遵守当前市场涨跌语义；
- 橙色：warning、风险或需要关注的状态；
- 其余图表系列减少无意义配色，优先通过线型、透明度和层级区分。

不为了模仿参考图新增不存在的市场 regime、行业权重、评分、donut 数据或业务字段。

### 4. 容器

主要研究区域采用扁平 panel：

- 减少大圆角；
- 默认去掉大面积 box-shadow；
- 使用 1px 低对比度分隔线；
- hover 不再通过明显上浮表达；
- 重要状态可以使用小型 badge，但避免药丸组件泛滥。

### 5. 导航

保留现有三段一级导航和 sticky 行为。外观从悬浮 segmented pill 调整为扁平研究 tab，当前项通过文字色、底部线或轻微底色强调。

### 6. 图表

继续使用 ECharts，不更换图表库。统一调整：

- grid 与 axis 颜色；
- tooltip；
- K 线和分时主线；
- VWAP 与关键价位；
- markLine；
- 研究图表的辅助系列透明度。

图表数据、缩放、交互和业务计算保持不变。

## 页面映射

### 盘前概览

继续使用当前 `InstrumentOverviewCard` 提供的数据。视觉上将标的卡片收敛为更紧凑的 market board / research list：价格与涨跌保持显著，代码、市场、数据状态和已有指标作为二级信息。

不新增参考图中的关注池评分、行业权重或其他不存在字段。

### 日内工作台

保留：

- 日线 / K 线；
- 分时；
- ATR；
- VWAP；
- ORB；
- KMeans 支撑阻力；
- 关键价位；
- 高级指标。

布局继续保持主图区 + 侧栏，只调整 panel、标题、控制条、指标表和图表 theme。

### 策略研究

继续由通用 `StrategySnapshot` 和 registry 驱动。Niu Men、R-Breaker 以及后续策略的指标表、provenance、quality 与对比视图统一采用高密度研究报告语言。

## 响应式与可访问性

- 390px 宽度继续不得产生文档级横向溢出；
- 研究表格可以在自己的 scroll container 内横向滚动；
- `focus-visible` 必须清楚；
- 颜色不能成为唯一状态信号；
- 深色与浅色模式均保留可读对比度。

## 实施边界

本次 UI PR 主要修改：

- `apps/dashboard/web/src/styles.css`
- `apps/dashboard/web/src/research.css`
- `apps/dashboard/web/src/theme.ts`
- 必要时对现有组件增加纯展示 class / wrapper
- `apps/dashboard/web/tests/e2e/dashboard.spec.mjs` 的视觉结构回归断言

不在该 PR 修改：

- 行情 provider；
- Redis；
- WebSocket contract；
- 策略计算；
- research wire contract；
- static snapshot 内容；
- M6 runtime 权限或 cutover。

## 验收标准

1. 三个一级区域和现有业务能力均保留。
2. 浅色模式形成一致的 editorial research 视觉语言。
3. dark mode 继续可用。
4. 不新增伪造业务指标或参考图专属内容。
5. K 线、分时、策略研究 ECharts 均正常渲染。
6. 390px 不产生页面级横向溢出。
7. 前端单元测试、Playwright 相关回归和 production build 通过后才可合并。
