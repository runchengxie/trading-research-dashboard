# 前端说明

Dashboard 前端是 React 单页应用，负责盘前概览、单证券日内工作台、策略研究和图表图片导出。行情与研究数据都以静态 JSON 形式提供，浏览器端没有 Python 服务或运行时 API。

## 技术栈

- React 19
- TypeScript
- Vite 8
- ECharts 6
- `echarts-for-react`
- Playwright

ECharts 使用按需注册，当前只加载实际使用的图表、组件和交互能力。生产 bundle 体积应通过构建结果持续观察，不在文档中固定记录某一次构建的 KB 数，避免依赖升级后说明很快失真。

## 数据来源

行情文件：

```text
web/public/data.json
```

仓库当前跟踪一份经过校验的 `data.json` 作为发布基线。需要刷新时，在可以访问可靠行情源或本地缓存的环境运行：

```bash
uv run python -m trading_research.dashboard.astock_tech \
  --json web/public/data.json
```

刷新后应执行：

```bash
python scripts/validate_static_assets.py
```

并通过 PR 审查快照变化。前端通过 `fetch('./data.json')` 读取，并要求响应内容类型确实是 JSON。这样可以识别静态托管把缺失资源错误回退成 `index.html` 的情况。

研究区域读取：

```text
web/public/research.json
```

仓库可以提交经过审查的研究发布基线。产品语义上研究快照仍是可选输入，缺少或无法解析时，策略研究区显示对应状态，盘前和日内行情区域继续工作。

## 目录结构

```text
web/
├── public/
│   ├── data.json                 # 必需、受审查的行情发布基线
│   └── research.json             # 可选研究发布基线
├── scripts/
│   ├── export-charts.mjs         # PNG 导出
│   └── export-charts.test.mjs
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api.ts
│   ├── types.ts
│   ├── priceLevels.ts
│   ├── researchSnapshot.ts
│   ├── research/
│   │   ├── strategySnapshot.ts
│   │   ├── niuMenAdapter.ts
│   │   └── strategyRegistry.ts
│   ├── styles.css
│   ├── theme.ts
│   └── components/
│       ├── InstrumentOverviewCard.tsx
│       ├── SelectedInstrumentWorkspace.tsx
│       ├── StrategyResearchView.tsx
│       ├── StrategyComparisonPanel.tsx
│       ├── StockChart.tsx
│       ├── IntradayChart.tsx
│       └── IndicatorTable.tsx
├── tests/e2e/
├── index.html
├── package.json
├── playwright.config.mjs
├── tsconfig.json
└── vite.config.ts
```

## 页面结构

页面没有前端路由，使用三个一级分区。

### 盘前概览

展示全部证券的轻量卡片，包括最新价格、涨跌幅、交易风格、VWAP、ATR 和最近交易日。选择卡片后可以进入对应证券的日内工作台。

### 日内工作台

展示当前证券的：

- K 线与成交量
- 上一交易日分时图
- VWAP、ATR、支撑和阻力
- 关键价格列表
- 可展开的高级指标

宽屏采用 12 列布局，图表为主区域，状态和关键价位位于侧栏。窄屏会降为单列。

### 策略研究

策略注册表负责声明研究入口和快照位置。当前牛门线读取 `research.json`，R-Breaker 入口保留 `rbreaker-research.json` 位置。

原始研究 JSON 先经过对应 adapter 转换成通用 `StrategySnapshot`，UI 组件只消费通用模型。新增策略时应把策略特有字段限制在解析和 adapter 边界，避免把策略 schema 直接散布到展示组件中。

## TypeScript 约束

`tsconfig.json` 已开启：

```text
strict
noUnusedLocals
noUnusedParameters
noFallthroughCasesInSwitch
```

`npm run build` 先执行 `tsc`，再执行 Vite 生产构建。因此生产构建本身已经承担 TypeScript 类型检查，不需要再维护一份功能重复的 typecheck 配置。

## 主题系统

UI 支持：

```text
light
dark
system
```

状态保存在：

```text
localStorage['theme']
```

`light` 和 `dark` 为显式主题，没有值时代表跟随系统。

主题分两层：

1. `styles.css` 使用 CSS 变量控制页面背景、卡片、文字、边框和状态颜色。
2. `theme.ts` 提供 ECharts 使用的浅色和深色 palette。

ECharts 内部颜色不能只依赖 CSS 变量，因此调整图表颜色时需要同步检查 `theme.ts`。

`index.html` 会在 React 挂载前读取主题偏好并设置 `<html data-theme>`，减少首屏主题闪烁。

## 图表图片导出

`web/scripts/export-charts.mjs` 使用 Playwright 截取浏览器已经渲染完成的页面组件，不重复实现 ECharts 配置。

导出内容包括：

- 盘前概览
- 每只证券的完整日内工作台
- 每只证券的 K 线面板
- 有分时数据时的分时面板
- `trading_research.chart_export.v1` manifest

本地构建后：

```bash
python ../scripts/validate_static_assets.py
npm run build
npm run export:charts
```

远程站点：

```bash
npm run export:charts -- \
  --url https://trading-research-dashboard.xiaowang01.workers.dev/ \
  --theme light
```

远程模式读取目标站点的当前 `data.json`。导出脚本要求 `stocks` 非空，并把 `generatedAt` 写入输出目录和 manifest，方便 cron 或 agent 判断截图数据日期。

自动化输出和 cron 示例见 [输出文件与目录结构](outputs.md)。

## 本地命令

```bash
cd web
npm ci
npm run dev
npm test
npm run build
npm run preview
npm run export:charts
```

浏览器相关操作第一次执行前安装 Chromium：

```bash
npx playwright install chromium
```

E2E：

```bash
npm run test:e2e
```

`playwright.config.mjs` 会使用 `dist/` 启动本地静态服务器，再执行 Chromium 验收测试。

当前根级 `Monorepo foundation` workflow 会运行前端单元测试和生产构建。为了控制 GitHub Actions 配额，不默认安装 Chromium，也不运行 Playwright E2E。需要浏览器验收或实际 PNG 导出时，应在具备 Playwright Chromium 的环境单独执行。

## 依赖安全

前端依赖由 `package-lock.json` 锁定。

常规检查：

```bash
npm ci
npm test
npm run build
npm audit --audit-level=high
```

依赖主版本升级应与对应单元测试和生产构建验证放在同一个 PR 中，避免锁文件、类型定义和实际 bundle 分开演进。
