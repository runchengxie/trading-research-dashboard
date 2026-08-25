# 前端说明

仪表盘的前端是一个 React 单页应用（SPA），图表在浏览器里渲染（不再由 Python 生成图片）。这份文档讲清楚技术栈、目录结构和主题系统，方便你本地改前端。

## 技术栈

* React 18 + TypeScript
* Vite 8（开发服务器与生产构建）
* ECharts（通过 `echarts-for-react` 封装）画 K 线、分时图

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
│   ├── App.tsx              # 主页面：股票卡片网格 + 主题 toggle + KPI chip
│   ├── api.ts               # fetch('./data.json')
│   ├── types.ts             # 数据类型定义
│   ├── styles.css           # 全部 CSS 变量 token（含 dark mode 覆盖块）
│   ├── theme.ts             # 图表配色 palette + useResolvedTheme hook
│   └── components/
│       ├── StockChart.tsx       # K 线 + 成交量（ECharts 蜡烛图）
│       ├── IntradayChart.tsx    # 上一交易日分时（ECharts 折线）
│       └── IndicatorTable.tsx   # 指标表 + 使用说明
├── index.html               # 含防主题闪烁（FOUC）内联脚本
└── package.json
```

页面是单页、无路由：所有股票以卡片网格平铺在同一页。

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
```

构建产物 `web/dist/` 是纯静态文件，可直接部署到 Cloudflare Pages 等任意静态托管（详见 [输出文件与目录结构](outputs.md)）。

## 依赖安全

前端依赖通过 `web/package-lock.json` 锁定。定期运行：

```bash
cd web
npm ci
npm audit
```

当前直接升级到 ECharts 6.1.0、Vite 8.2.0 和 `@vitejs/plugin-react` 6.1.0 后，审计结果为 0 个漏洞。升级涉及主版本变化，因此构建验证应与依赖变更放在同一个 PR 中完成。
