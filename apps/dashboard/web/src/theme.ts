import { useEffect, useState } from 'react';

/**
 * 主题切换模块。
 *
 * 设计要点：
 * 1. CSS 变量（`:root` / `[data-theme="dark"]`）负责页面外壳换肤。
 * 2. ECharts 内部颜色不读 CSS 变量，所以这里维护两套 {@link ChartPalette}，
 *    由 StockChart / IntradayChart 根据 `theme` prop 选择。
 * 3. 三态主题：light / dark / system。`system` 时跟随 `prefers-color-scheme`。
 * 4. localStorage key 固定为 `theme`，空值表示 system。
 *
 * 之所以用 prop 而不是 context：两个图表组件 `useMemo` 依赖里只用 `theme` 字符串，
 * 直接传字符串最稳定，避免每次 render 生成新对象导致 ECharts 误判重渲染。
 */

export type ThemeMode = 'light' | 'dark';
export type ThemeChoice = ThemeMode | 'system';

export interface ChartPalette {
  /** 涨色 / 跌色（A 股惯例：红涨绿跌）。 */
  up: string;
  down: string;
  /** K 线标记线：聚类支撑 / 阻力 / 关键价 / 中枢。 */
  levelSupport: string;
  levelResistance: string;
  levelKey: string;
  levelCenter: string;
  /** 图表坐标轴线 / 坐标轴 label 文字。 */
  axisLineColor: string;
  axisLabelColor: string;
  /** 主网格线和次网格线，保持低对比度以免抢过价格走势。 */
  gridColor: string;
  minorGridColor: string;
  /** tooltip 标签背景色（hover cross 时显示数值的小灰底）。 */
  tooltipBg: string;
  /** 分时图价格线 / VWAP 横线。 */
  lineColor: string;
  vwapColor: string;
  /** 分时图标题文字色。 */
  titleColor: string;
}

export const LIGHT_PALETTE: ChartPalette = {
  up: '#ef232a',
  down: '#14b143',
  levelSupport: '#2563eb',
  levelResistance: '#6d5bd0',
  levelKey: '#b96800',
  levelCenter: '#7257a8',
  axisLineColor: '#9ba3ab',
  axisLabelColor: '#5f6872',
  gridColor: '#e1e6ec',
  minorGridColor: '#f0f2f5',
  tooltipBg: '#232a33',
  lineColor: '#1267d6',
  vwapColor: '#c77612',
  titleColor: '#3e4752',
};

export const DARK_PALETTE: ChartPalette = {
  up: '#ef4444',
  down: '#22c55e',
  levelSupport: '#66a8ff',
  levelResistance: '#b8a1ff',
  levelKey: '#f2a94b',
  levelCenter: '#c2b4df',
  axisLineColor: '#66717d',
  axisLabelColor: '#aab2bc',
  gridColor: 'rgba(155, 175, 195, 0.13)',
  minorGridColor: 'rgba(155, 175, 195, 0.045)',
  tooltipBg: '#080b0f',
  lineColor: '#66a8ff',
  vwapColor: '#f2a94b',
  titleColor: '#c4cad0',
};

const STORAGE_KEY = 'theme';

function readChoice(): ThemeChoice {
  if (typeof window === 'undefined') return 'system';
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === 'light' || v === 'dark' ? v : 'system';
}

function systemPrefersDark(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export interface ResolvedTheme {
  /** 用户当前选择（含 'system'）。 */
  choice: ThemeChoice;
  /** 实际生效的主题（'system' 时已解析）。 */
  resolved: ThemeMode;
  /** 切换：传 'light' / 'dark' / 'system'。 */
  setChoice: (next: ThemeChoice) => void;
}

export function useResolvedTheme(): ResolvedTheme {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => readChoice());
  const [systemDark, setSystemDark] = useState<boolean>(() => systemPrefersDark());

  // 监听系统偏好变化；只在 choice === 'system' 时实际生效
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const resolved: ThemeMode =
    choice === 'system' ? (systemDark ? 'dark' : 'light') : choice;

  const setChoice = (next: ThemeChoice) => {
    setChoiceState(next);
    if (typeof window !== 'undefined') {
      if (next === 'system') window.localStorage.removeItem(STORAGE_KEY);
      else window.localStorage.setItem(STORAGE_KEY, next);
    }
  };

  return { choice, resolved, setChoice };
}

export function paletteFor(mode: ThemeMode): ChartPalette {
  return mode === 'dark' ? DARK_PALETTE : LIGHT_PALETTE;
}
