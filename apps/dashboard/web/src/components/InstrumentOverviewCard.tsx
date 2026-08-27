import { currentPrice, isUsInstrument, liveStatusLabel } from '../liveQuote.ts';
import type { StockData } from '../types';

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined || Number.isNaN(value)
    ? '—'
    : value.toFixed(2);
}

function changeFromDaily(stock: StockData): number | null {
  const live = stock.liveQuote?.freshness === 'current';
  const latest = currentPrice(stock);
  const previous = live
    ? stock.daily[stock.daily.length - 1]?.close ?? stock.indicators.lastClose
    : stock.daily[stock.daily.length - 2]?.close;
  if (latest === null || previous === null || previous === undefined || previous === 0) {
    return null;
  }
  return ((latest - previous) / previous) * 100;
}

export default function InstrumentOverviewCard({
  stock,
  selected,
  onSelect,
}: {
  stock: StockData;
  selected: boolean;
  onSelect: () => void;
}) {
  const lastClose = currentPrice(stock);
  const change = changeFromDaily(stock);
  const changeClass = change === null ? '' : change >= 0 ? 'up' : 'down';

  return (
    <button
      type="button"
      className={`instrument-overview-card${selected ? ' selected' : ''}`}
      data-code={stock.code}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <span className="instrument-card-topline">
        <span>
          <strong>{stock.name}</strong>
          <span className="instrument-code">{stock.code}</span>
        </span>
        <span className="instrument-card-chevron" aria-hidden="true">
          →
        </span>
      </span>

      <span className="instrument-price-row">
        <span className="instrument-price">{formatNumber(lastClose)}</span>
        <span className={`instrument-change ${changeClass}`}>
          {change === null ? '涨跌 —' : `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`}
        </span>
      </span>

      <span className="instrument-card-status">
        <span className="instrument-status-dot" aria-hidden="true" />
        {stock.tradingStyle}
        {isUsInstrument(stock) ? ` · ${liveStatusLabel(stock)}` : ''}
      </span>

      <span className="instrument-card-metrics">
        <span>
          <small>VWAP</small>
          <b>{formatNumber(stock.indicators.vwap)}</b>
        </span>
        <span>
          <small>ATR20</small>
          <b>{formatNumber(stock.indicators.atr20)}</b>
        </span>
        <span>
          <small>交易日</small>
          <b>{stock.lastTradeDay}</b>
        </span>
      </span>
    </button>
  );
}
