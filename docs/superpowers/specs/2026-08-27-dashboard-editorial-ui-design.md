# Dashboard Editorial Research UI 设计

## 状态

本设计已在对话中确认。参考图仅作为 UI 设计语言来源；Dashboard 的业务内容、行情字段、策略指标和信息架构继续由本项目自身的数据与功能决定。

## 目标

将 `apps/dashboard/web` 的视觉语言从偏 SaaS 的圆角卡片工作台，收敛为更适合金融研究的 editorial / internal-audit 风格，同时保留现有三个一级区域：盘前概览、日内工作台、策略研究。功能、数据契约和策略计算不因为换肤改变。

## 视觉原则

浅色模式使用略暖的研究纸张底色与极低对比度辅助网格。页面主体依靠留白和分隔线组织，减少悬浮白卡。深色模式继续保留，采用同一层级系统的 dark research terminal 表达。

文字层级稳定为 kicker、区域标题、正文/指标名、metadata。数字、证券代码、日期和指标值使用 tabular numerals。

蓝色用于主结构与当前选择；红/绿继续遵守当前市场涨跌语义；橙色用于 warning / risk。减少无意义图表配色，不为了模仿参考图新增不存在的 regime、行业权重、评分或业务字段。

主要研究区域使用扁平 panel：减少大圆角、默认去掉大面积 box-shadow、使用 1px 低对比度分隔线、hover 不明显上浮。保留清晰 focus-visible。

一级导航保留 sticky 行为，从悬浮 segmented pill 调整为扁平 research tabs。ECharts 继续使用现有组件与数据，只调整 grid、axis、tooltip、主线、VWAP 和关键价位 palette。

## 页面映射

盘前概览继续使用当前 `InstrumentOverviewCard` 数据，视觉收敛为紧凑 market board。日内工作台保留日线/K线、分时、ATR、VWAP、ORB、KMeans 支撑阻力、关键价位和高级指标。策略研究继续由通用 `StrategySnapshot` 和 registry 驱动。

## 响应式与可访问性

390px 宽度不得产生文档级横向溢出；研究表格允许在自身 scroll container 内滚动；颜色不能成为唯一状态信号；深浅主题都要保留可读对比度。

## 实施边界

主要修改 `apps/dashboard/web/src/styles.css`、`research.css`、`theme.ts`，必要时只为展示增加 class/wrapper。不修改行情 provider、Redis、WebSocket contract、策略计算、research wire contract、static snapshot 内容和 M6 权限/cutover。

## 验收标准

1. 三个一级区域和现有业务能力均保留。
2. 浅色模式形成一致 editorial research 视觉语言。
3. dark mode 继续可用。
4. 不新增伪造业务指标。
5. 现有 ECharts 正常渲染。
6. 390px 不产生页面级横向溢出。
7. 前端单元测试、Playwright 回归和 production build 通过后才可合并。
