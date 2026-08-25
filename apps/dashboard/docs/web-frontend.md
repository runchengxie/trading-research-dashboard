# 前端说明

仪表盘的前端是一个 React 单页应用（SPA），图表在浏览器里渲染（不再由 Python 生成图片）。这份文档讲清楚技术栈、产品分区、策略注册表、目录结构和主题系统，方便你本地改前端。

## 技术栈

* React 19 + TypeScript
* Vite 8（开发服务器与生产构建）
* ECharts（通过 `echarts-for-react/lib/core` 封装）画 K 线、分时图

前端只注册当前使用的蜡烛图、柱状图、折线图、缩放、提示框和标记线组件，不引入 ECharts 完整构建。当前生产构建主 JavaScript chunk 约 822 KB，gzip 后约 272 KB。Vite 的提醒阈值为 800 KB，React 19 升级后构建会显示体积提醒，后续可以单独评估懒加载或继续拆包。

## 数据来源

* 数据来自 `web/public/data.json`，由 Python 脚本 `astock_tech.py --json web/public/data.json` 在构建时生成
* 运行时前端只 `fetch('./data.json')` 读取这个静态文件，**没有后端、没有运行时接口**
* 所以前端改动与数据层完全解耦：改样式/组件不用碰 Python，也不用担心数据延迟

## 目录结构

```text
web/
├── public/
│   └── data.json            # 构建时由 Python 生成，前端运行时读取
├── src/
│   ├── main.tsx             # 挂载入口
│   ├── App.tsx              # 主页面：盘前概览 / 日内工作台 / 策略研究三段式导航
│   ├── api.ts               # fetch('./data.json')
│   ├── types.ts             # 数据类型定义
│   ├── priceLevels.ts       # 关键价位过滤与距离百分比
│   ├── researchSnapshot.ts  # Niu Men v1/v2 原始快照解析
│   ├── research/
│   │   ├── strategySnapshot.ts # 通用策略快照模型
│   │   ├── niuMenAdapter.ts    # Niu Men v2 → 通用模型
│   │   └── strategyRegistry.ts # 策略入口与快照路径
│   ├── styles.css           # 全部 CSS 变量 token（含 dark mode 覆盖块）
│   ├── theme.ts             # 图表配色 palette + useResolvedTheme hook
│   └── components/
│       ├── InstrumentOverviewCard.tsx # 标的概览卡与选中状态
│       ├── SelectedInstrumentWorkspace.tsx # 当前标的的图表、指标与关键价位
│       ├── StrategyResearchView.tsx # 策略子 Tab 和局部加载状态
│       ├── StrategyComparisonPanel.tsx # 已发布策略的共同指标对比
│       ├── StockChart.tsx       # K 线 + 成交量（ECharts 蜡烛图）
│       ├── IntradayChart.tsx    # 上一交易日分时（ECharts 折线）
│       └── IndicatorTable.tsx   # 指标表 + 使用说明
├── index.html               # 含防主题闪烁（FOUC）内联脚本
└── package.json
```

页面是单页、无路由，但有三个产品分区：盘前概览展示所有标的的轻量卡片；日内工作台只展示当前选中标的的 K 线、分时、指标和关键价位；策略研究通过策略注册表承载不同策略的快照。

研究区域的牛门线入口读取 `research.json`，R-Breaker 入口预留 `rbreaker-research.json`。R-Breaker 快照尚未发布时只显示待发布状态，不制造任何研究数值；对比页在至少有两个有效快照后才显示指标表。

研究原始 JSON 仍由各策略仓库负责解析和导出。前端只消费 adapter 转换后的 `StrategySnapshot`，因此未来增加策略时只需新增快照 adapter 和注册表项，不需要把新策略字段散落到 `ResearchPanel`。

日内工作台采用 12 列 Bento 网格：宽屏下主图表占 8 列，右侧状态与指标占 4 列；窄屏自动退化为单列。K 线保留全部分析价位线，但默认只显示最近支撑、最近阻力和关键结构标签，可通过“显示全部价位”恢复完整标签。支撑和阻力同时显示相对于当前价的距离百分比，高级指标默认折叠。

概览卡与研究数据共用现有静态文件契约，不新增后端接口，也不改变 Python 指标计算。关键价位使用蓝 / 紫 / 琥珀色，涨跌仍使用 A 股红 / 绿，避免价格行为和模型标注产生语义冲突。

## 主题系统

前端支持三态主题：**浅色 / 深色 / 跟随系统**，默认「跟随系统」。

* 状态存在 `localStorage['theme']`，值为 `light` / `dark` / 不写（=system）
* 页面右上角按钮在三态间循环切换：浅 → 深 → 跟随系统 → 浅
* 跟随系统时，实时监听 `prefers-color-scheme` 变化

### 为什么分两层

ECharts 内部的图表颜色不读 CSS 变量，所以主题切换要分两层处理：

1. **页面外壳**：`styles.css` 里用 CSS 变量 token（如 `--bg`、`--card-bg`、`--text`），并在 `[data-theme="dark"]` 下覆盖一套深色值。改这里即可换页面背景、卡片、文字、边框。
2. **图表内部**：`theme.ts` 提供 `LIGHT_PALETTE` 与 `DARK_PALETTE` 两套颜色（涨/跌、标记线、坐标轴、分时线、VWAP 等），由 `useResolvedTheme()` 返回当前生效的 `resolved`（light/dark），`App.tsx` 把它作为 `theme` prop 透传给 `StockChart` / `IntradayChart`，组件内 `useMemo` 据此选 palette。

如果只改 CSS 变量，图表会因为颜色是硬编码而保持浅色，出现「深色页面壳 + 浅色图表」的拼接撕裂。所以改图表配色必须动 `theme.ts`。

### 防闪烁（FOUC）

`index.html` 在 `<head>` 里有一段内联脚本，在 React 挂载前就读 `localStorage` 与系统偏好，把 `data-theme` 写到 `<html>` 上。这样首屏 CSS 立即按正确主题渲染，避免先闪浅色再跳深色。

### 改主题相关代码时改哪里

* 页面配色 / 圆角 / 阴影 / 字号 → `styles.css`
* 图表颜色（涨绿跌红、标记线、坐标轴） → `theme.ts` 的 `LIGHT_PALETTE` / `DARK_PALETTE`
* 切换逻辑、KPI chip、toggle 按钮 → `App.tsx`
* 某个图表的具体画法 → 对应 `components/*.tsx`

## 本地命令

```bash
cd web
npm install            # 首次装依赖
npm run dev            # 开发服务器 http://localhost:5173
npm run build          # 生产构建，产物在 web/dist/
npm run preview        # 本地起服务预览 dist/，http://localhost:4173
npm run test:unit      # 前端单元测试
npx playwright install chromium  # 首次运行浏览器验收时安装浏览器
npm run test:e2e       # Chromium 验收测试
```

浏览器验收依赖 `@playwright/test`，版本锁定在 `package-lock.json`。CI 会安装 Chromium，开发机首次运行时需要执行 `npx playwright install chromium`。测试会先使用 `web/playwright.config.mjs` 构建并托管 `dist`，再验证页面渲染、研究快照降级、主题切换和手机宽度布局。

构建产物 `web/dist/` 是纯静态文件，可直接部署到 Cloudflare Pages 等任意静态托管（详见 [输出文件与目录结构](outputs.md)）。

## 依赖安全

前端依赖通过 `web/package-lock.json` 锁定。定期运行：

```bash
cd web
npm ci
npm audit
```

当前直接升级到 ECharts 6.1.0、Vite 8.2.0 和 `@vitejs/plugin-react` 6.1.0 后，审计结果为 0 个漏洞。升级涉及主版本变化，因此构建验证应与依赖变更放在同一个 PR 中完成。
