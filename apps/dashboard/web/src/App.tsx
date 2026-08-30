import { useEffect, useState } from 'react';
import { loadDashboard, loadStrategySnapshot, type StrategyLoadResult } from './api.ts';
import { applyLiveQuote, buildLiveStreamUrl, isUsInstrument } from './liveQuote.ts';
import type { DashboardData, LiveQuote, Market, StockData } from './types.ts';
import InstrumentOverviewCard from './components/InstrumentOverviewCard';
import StrategyResearchView from './components/StrategyResearchView';
import SelectedInstrumentWorkspace from './components/SelectedInstrumentWorkspace';
import { parseContextualResearch } from './contextualResearch.ts';
import { STRATEGY_DEFINITIONS } from './research/strategyRegistry.ts';
import { useResolvedTheme, type ThemeChoice } from './theme';

/** 切换顺序：light → dark → system → light ... */
const CYCLE: ThemeChoice[] = ['light', 'dark', 'system'];
const CHOICE_LABEL: Record<ThemeChoice, string> = {
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
};

type ViewId = 'overview' | 'workspace' | 'research';
type MarketFilter = 'ALL' | Market;

const MARKET_FILTERS: { id: MarketFilter; label: string }[] = [
  { id: 'ALL', label: '全部市场' },
  { id: 'CN', label: 'A股' },
  { id: 'HK', label: '港股' },
  { id: 'US', label: '美股' },
];

const NAV_ITEMS: { id: ViewId; label: string }[] = [
  { id: 'overview', label: '盘前概览' },
  { id: 'workspace', label: '日内工作台' },
  { id: 'research', label: '策略研究' },
];

function isLiveQuote(value: unknown): value is LiveQuote {
  if (typeof value !== 'object' || value === null) return false;
  const quote = value as Partial<LiveQuote>;
  return (
    typeof quote.symbol === 'string' &&
    typeof quote.price === 'number' &&
    Number.isFinite(quote.price) &&
    typeof quote.timestamp === 'string' &&
    typeof quote.source === 'string' &&
    (quote.status === 'live' || quote.status === 'delayed') &&
    (quote.freshness === 'current' || quote.freshness === 'stale' || quote.freshness === 'unknown')
  );
}

function marketOf(stock: StockData): Market {
  if (stock.market) return stock.market;
  if (isUsInstrument(stock)) return 'US';
  if (/^(?:hk\d+|\d+\.hk)$/i.test(stock.code)) return 'HK';
  return 'CN';
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [strategyResults, setStrategyResults] = useState<StrategyLoadResult[]>([]);
  const [researchLoaded, setResearchLoaded] = useState(false);
  const [activeView, setActiveView] = useState<ViewId>('overview');
  const [activeResearchTab, setActiveResearchTab] = useState('niu-men-line');
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [activeMarket, setActiveMarket] = useState<MarketFilter>('ALL');
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

  const marketDataUrl = import.meta.env.VITE_MARKET_DATA_URL?.trim() ?? '';
  const liveUsCodes =
    data?.stocks
      .filter(isUsInstrument)
      .map((stock) => stock.code)
      .sort()
      .join(',') ?? '';

  useEffect(() => {
    if (!marketDataUrl || !liveUsCodes) return;

    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const markQuotesStale = () => {
      setData((current) => {
        if (!current) return current;
        return {
          ...current,
          stocks: current.stocks.map((stock) =>
            stock.liveQuote
              ? { ...stock, liveQuote: { ...stock.liveQuote, freshness: 'stale' as const } }
              : stock,
          ),
        };
      });
    };

    const connect = () => {
      if (disposed) return;
      try {
        socket = new WebSocket(buildLiveStreamUrl(marketDataUrl, liveUsCodes.split(',')));
      } catch {
        markQuotesStale();
        return;
      }

      socket.onmessage = (event) => {
        let value: unknown;
        try {
          value = JSON.parse(String(event.data));
        } catch {
          return;
        }
        if (!isLiveQuote(value)) return;
        setData((current) => {
          if (!current) return current;
          return {
            ...current,
            stocks: current.stocks.map((stock) => applyLiveQuote(stock, value)),
          };
        });
      };

      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (disposed) return;
        markQuotesStale();
        reconnectTimer = window.setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [marketDataUrl, liveUsCodes]);

  useEffect(() => {
    if (!data) return;
    let active = true;
    setResearchLoaded(false);
    Promise.all(
      STRATEGY_DEFINITIONS.map((definition) =>
        loadStrategySnapshot(definition, data.generatedAt),
      ),
    )
      .then((results) => {
        if (active) setStrategyResults(results);
      })
      .finally(() => {
        if (active) setResearchLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [data?.generatedAt]);

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
          请在 <code>apps/dashboard/</code> 运行{' '}
          <code>uv run python -m trading_research.dashboard.astock_tech --json web/public/data.json</code>{' '}
          生成有效行情快照，再执行 <code>python scripts/validate_static_assets.py</code>。
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

  const filteredStocks = data.stocks.filter(
    (stock) => activeMarket === 'ALL' || marketOf(stock) === activeMarket,
  );

  const selectedStock =
    filteredStocks.find((stock) => stock.code === selectedCode) ?? filteredStocks[0] ?? null;
  const contextualResearch = parseContextualResearch(
    (data as DashboardData & { contextualResearch?: unknown }).contextualResearch,
  );

  return (
    <div className="container">
      <header className="page-header">
        <div>
          <p className="brand-kicker">TRADING DASHBOARD</p>
          <h1>Trading Dashboard</h1>
          <p className="subtitle">行情研究与日内工作台 · 行情数据日期：{data.generatedAt}</p>
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

            <div className="market-switcher" aria-label="市场筛选">
              <span className="market-switcher-label">市场筛选</span>
              {MARKET_FILTERS.map((filter) => {
                const count = filter.id === 'ALL'
                  ? data.stocks.length
                  : data.stocks.filter((stock) => marketOf(stock) === filter.id).length;
                return (
                  <button
                    type="button"
                    className={`market-switcher-button${activeMarket === filter.id ? ' active' : ''}`}
                    aria-pressed={activeMarket === filter.id}
                    key={filter.id}
                    onClick={() => setActiveMarket(filter.id)}
                  >
                    {filter.label} <span>{count}</span>
                  </button>
                );
              })}
            </div>

            {filteredStocks.length === 0 && (
              <div className="empty-market-state">
                <strong>当前快照没有{MARKET_FILTERS.find((item) => item.id === activeMarket)?.label}标的。</strong>
                {activeMarket === 'US' && (
                  <span>请生成快照时传入 <code>--codes AAPL.US,MSFT.US</code>，或使用市场数据服务的 yfinance 回退。</span>
                )}
              </div>
            )}

            {data.stocks.length === 0 && (
              <div className="error-box">本期没有成功处理的股票。</div>
            )}

            <div className="instrument-overview-grid">
              {filteredStocks.map((stock) => (
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
            <SelectedInstrumentWorkspace
              stock={selectedStock}
              theme={resolved}
              contextualResearch={contextualResearch}
            />
          ) : (
            <div className="error-box">暂无标的可以进入日内工作台。</div>
          )
        )}

        {activeView === 'research' && (
          <StrategyResearchView
            results={strategyResults}
            loaded={researchLoaded}
            activeTab={activeResearchTab}
            onTabChange={setActiveResearchTab}
            theme={resolved}
          />
        )}
      </main>

      <footer className="page-footer">
        行情来源：akshare / tushare / Alpaca（可选实时） · Trading Dashboard · 仅供研究，不构成投资建议
      </footer>
    </div>
  );
}
