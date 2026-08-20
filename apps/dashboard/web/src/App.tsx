import { useEffect, useState } from 'react';
import { loadDashboard } from './api';
import type { DashboardData, StockData } from './types';
import StockChart from './components/StockChart';
import IntradayChart from './components/IntradayChart';
import IndicatorTable from './components/IndicatorTable';
import { useResolvedTheme, type ThemeChoice } from './theme';

/** 切换顺序：light → dark → system → light ... */
const CYCLE: ThemeChoice[] = ['light', 'dark', 'system'];
const CHOICE_LABEL: Record<ThemeChoice, string> = {
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
};

/**
 * KPI chip 行：股票卡片头部下方三颗药丸。
 * 仅复用已有 indicators 字段，不引入新数据。
 */
function KpiChips({ stock }: { stock: StockData }) {
  const fmt = (v: number | null | undefined) =>
    v === null || v === undefined || Number.isNaN(v) ? '—' : v.toFixed(2);
  const ind = stock.indicators;
  return (
    <div className="kpi-row">
      <span className="kpi-chip">
        最新价
        <span className="kpi-value">{fmt(ind.lastClose)}</span>
      </span>
      <span className="kpi-chip">
        20日ATR
        <span className="kpi-value">{fmt(ind.atr20)}</span>
      </span>
      <span className="kpi-chip">
        上一日VWAP
        <span className="kpi-value">{fmt(ind.vwap)}</span>
      </span>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { choice, resolved, setChoice } = useResolvedTheme();

  // 把 resolved theme 同步到 <html data-theme>，让 CSS 切换生效
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
  }, [resolved]);

  useEffect(() => {
    loadDashboard()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const cycleChoice = () => {
    const i = CYCLE.indexOf(choice);
    const next = CYCLE[(i + 1) % CYCLE.length];
    setChoice(next);
  };

  if (error) {
    return (
      <div className="container">
        <div className="error-box">
          加载失败：{error}
          <br />
          请先运行 <code>uv run python astock_tech.py --json web/public/data.json</code> 生成数据。
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container">
        <div className="loading">加载中…</div>
      </div>
    );
  }

  return (
    <div className="container">
      <header className="page-header">
        <div>
          <h1>A股 T+0 交易仪表盘</h1>
          <p className="subtitle">数据日期：{data.generatedAt}</p>
        </div>
        <button
          type="button"
          className="theme-toggle"
          onClick={cycleChoice}
          title={`当前主题：${CHOICE_LABEL[choice]}（点击切换）`}
          aria-label="切换主题"
        >
          {resolved === 'dark' ? '🌙' : '☀'}
        </button>
      </header>

      {data.stocks.length === 0 && (
        <div className="error-box">本期没有成功处理的股票。</div>
      )}

      <div className="stock-grid">
        {data.stocks.map((stock) => (
          <section className="stock-card" key={stock.code}>
            <div className="stock-card-head">
              <h2>
                {stock.name} <span className="code">{stock.code}</span>
              </h2>
              <p className="meta">
                {stock.tradingStyle} · 最近交易日 {stock.lastTradeDay}
              </p>
            </div>

            <KpiChips stock={stock} />

            <StockChart stock={stock} theme={resolved} />
            <div className="panel-row">
              <IndicatorTable stock={stock} />
            </div>
            <IntradayChart stock={stock} theme={resolved} />
          </section>
        ))}
      </div>

      <footer className="page-footer">
        数据来源：akshare / tushare · 仅供研究，不构成投资建议
      </footer>
    </div>
  );
}
