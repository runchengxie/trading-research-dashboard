import { useEffect, useState } from 'react';
import { loadDashboard, loadResearch } from './api';
import type { DashboardData, ResearchSnapshot } from './types';
import InstrumentOverviewCard from './components/InstrumentOverviewCard';
import ResearchPanel from './components/ResearchPanel';
import SelectedInstrumentWorkspace from './components/SelectedInstrumentWorkspace';
import { useResolvedTheme, type ThemeChoice } from './theme';

/** 切换顺序：light → dark → system → light ... */
const CYCLE: ThemeChoice[] = ['light', 'dark', 'system'];
const CHOICE_LABEL: Record<ThemeChoice, string> = {
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
};

type ViewId = 'overview' | 'workspace' | 'research';

const NAV_ITEMS: { id: ViewId; label: string }[] = [
  { id: 'overview', label: '盘前概览' },
  { id: 'workspace', label: '日内工作台' },
  { id: 'research', label: '策略研究' },
];

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [research, setResearch] = useState<ResearchSnapshot | null>(null);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [researchLoaded, setResearchLoaded] = useState(false);
  const [activeView, setActiveView] = useState<ViewId>('overview');
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
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

  useEffect(() => {
    let active = true;
    loadResearch()
      .then((snapshot) => {
        if (active) setResearch(snapshot);
      })
      .catch((e) => {
        if (active) setResearchError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (active) setResearchLoaded(true);
      });
    return () => {
      active = false;
    };
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

  const selectedStock =
    data.stocks.find((stock) => stock.code === selectedCode) ?? data.stocks[0] ?? null;

  return (
    <div className="container">
      <header className="page-header">
        <div>
          <p className="brand-kicker">TRADING RESEARCH WORKBENCH</p>
          <h1>A股交易研究仪表盘</h1>
          <p className="subtitle">行情数据日期：{data.generatedAt} · 研究、观察与复盘分层呈现</p>
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

      <nav className="section-nav" aria-label="仪表盘分区">
        {NAV_ITEMS.map((item) => (
          <button
            type="button"
            className={`section-nav-button${activeView === item.id ? ' active' : ''}`}
            aria-current={activeView === item.id ? 'page' : undefined}
            key={item.id}
            onClick={() => setActiveView(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <main>
        {activeView === 'overview' && (
          <section className="overview-section" aria-labelledby="overview-title">
            <div className="section-heading">
              <div>
                <p className="section-kicker">盘前与日内</p>
                <h2 id="overview-title">标的概览</h2>
                <p className="section-subtitle">
                  先看市场状态，再选择一个标的进入日内工作台。
                </p>
              </div>
              <span className="data-status">
                <span className="data-status-dot" aria-hidden="true" />
                数据正常
              </span>
            </div>

            {data.stocks.length === 0 && (
              <div className="error-box">本期没有成功处理的股票。</div>
            )}

            <div className="instrument-overview-grid">
              {data.stocks.map((stock) => (
                <InstrumentOverviewCard
                  stock={stock}
                  selected={stock.code === selectedStock?.code}
                  onSelect={() => setSelectedCode(stock.code)}
                  key={stock.code}
                />
              ))}
            </div>

            {selectedStock && (
              <div className="overview-next-step">
                当前选择：<strong>{selectedStock.name}</strong>
                <button type="button" onClick={() => setActiveView('workspace')}>
                  打开日内工作台 →
                </button>
              </div>
            )}
          </section>
        )}

        {activeView === 'workspace' && (
          selectedStock ? (
            <SelectedInstrumentWorkspace stock={selectedStock} theme={resolved} />
          ) : (
            <div className="error-box">暂无标的可以进入日内工作台。</div>
          )
        )}

        {activeView === 'research' && (
          <ResearchPanel
            snapshot={research}
            loaded={researchLoaded}
            error={researchError}
            theme={resolved}
            dashboardDate={data.generatedAt}
          />
        )}
      </main>

      <footer className="page-footer">
        行情来源：akshare / tushare · 策略研究：niu-men-line-strategy · 仅供研究，不构成投资建议
      </footer>
    </div>
  );
}
