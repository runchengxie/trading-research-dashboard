import type { StockData, LevelType } from '../types';
import IntradayChart from './IntradayChart';
import IndicatorTable from './IndicatorTable';
import StockChart from './StockChart';
import type { ThemeMode } from '../theme';

const LEVEL_LABELS: Record<LevelType, string> = {
  support: '支撑',
  resistance: '阻力',
  key: '关键',
  center: '中枢',
};

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined || Number.isNaN(value)
    ? '—'
    : value.toFixed(2);
}

export default function SelectedInstrumentWorkspace({
  stock,
  theme,
}: {
  stock: StockData;
  theme: ThemeMode;
}) {
  const lastClose = stock.daily[stock.daily.length - 1]?.close ?? stock.indicators.lastClose;
  const levels = stock.levels.length > 0 ? stock.levels : [];

  return (
    <section className="selected-instrument-workspace" aria-labelledby="selected-workspace-title">
      <header className="workspace-header">
        <div>
          <p className="section-kicker">当前选择</p>
          <h2 id="selected-workspace-title">
            日内工作台 · {stock.name} <span className="code">{stock.code}</span>
          </h2>
          <p className="workspace-subtitle">
            {stock.tradingStyle} · 最近交易日 {stock.lastTradeDay}
          </p>
        </div>
        <div className="workspace-price-summary">
          <span className="workspace-price-label">最新价</span>
          <strong>{formatNumber(lastClose)}</strong>
        </div>
      </header>

      <div className="workspace-grid">
        <div className="workspace-chart-column">
          <section className="workspace-panel chart-panel" aria-labelledby="daily-chart-title">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">价格结构</p>
                <h3 id="daily-chart-title">K线与成交量</h3>
              </div>
              <span className="panel-hint">可拖动时间轴查看历史区间</span>
            </div>
            <StockChart stock={stock} theme={theme} />
          </section>

          <section className="workspace-panel intraday-panel" aria-labelledby="intraday-chart-title">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">日内行为</p>
                <h3 id="intraday-chart-title">上一交易日分时</h3>
              </div>
            </div>
            {stock.intraday && stock.intraday.length > 0 ? (
              <IntradayChart stock={stock} theme={theme} />
            ) : (
              <p className="empty-panel">暂无可用分时数据。</p>
            )}
          </section>
        </div>

        <aside className="workspace-side-column">
          <section className="workspace-panel state-panel" aria-labelledby="state-title">
            <div className="panel-heading compact">
              <div>
                <p className="section-kicker">今日交易状态</p>
                <h3 id="state-title">观察重点</h3>
              </div>
              <span className="state-badge">{stock.tradingStyle}</span>
            </div>
            <dl className="state-metrics">
              <div>
                <dt>VWAP</dt>
                <dd>{formatNumber(stock.indicators.vwap)}</dd>
              </div>
              <div>
                <dt>ATR20</dt>
                <dd>{formatNumber(stock.indicators.atr20)}</dd>
              </div>
              <div>
                <dt>支撑位</dt>
                <dd>{formatNumber(stock.indicators.support)}</dd>
              </div>
              <div>
                <dt>阻力位</dt>
                <dd>{formatNumber(stock.indicators.resistance)}</dd>
              </div>
            </dl>
          </section>

          <section className="workspace-panel levels-panel" aria-labelledby="levels-title">
            <div className="panel-heading compact">
              <div>
                <p className="section-kicker">价格结构</p>
                <h3 id="levels-title">关键价位</h3>
              </div>
            </div>
            {levels.length === 0 ? (
              <p className="empty-panel">暂无关键价位。</p>
            ) : (
              <ul className="key-level-list">
                {levels.map((level, index) => (
                  <li className={`key-level-item key-level-${level.type}`} key={`${level.type}-${level.value}-${index}`}>
                    <span className="key-level-label">
                      <span className="key-level-marker" aria-hidden="true" />
                      {level.label || LEVEL_LABELS[level.type]}
                    </span>
                    <strong>{formatNumber(level.value)}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="workspace-panel indicators-panel" aria-labelledby="indicators-title">
            <div className="panel-heading compact">
              <div>
                <p className="section-kicker">模型读数</p>
                <h3 id="indicators-title">指标明细</h3>
              </div>
            </div>
            <IndicatorTable stock={stock} />
          </section>
        </aside>
      </div>
    </section>
  );
}
