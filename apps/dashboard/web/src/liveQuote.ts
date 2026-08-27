import type { LiveQuote, StockData } from './types.ts';

function usTickerFromCode(code: string, explicitUs = false): string | null {
  const value = code.trim();
  const canonical = /^us:(?<ticker>[A-Z][A-Z0-9.-]{0,14})$/i.exec(value);
  if (canonical?.groups?.ticker) return canonical.groups.ticker.toUpperCase();

  const suffixed = /^(?<ticker>[A-Z][A-Z0-9.-]{0,14})\.US$/i.exec(value);
  if (suffixed?.groups?.ticker) return suffixed.groups.ticker.toUpperCase();

  if (explicitUs && /^[A-Z][A-Z0-9.-]{0,14}$/i.test(value)) {
    return value.toUpperCase();
  }
  return null;
}

export function isUsInstrument(stock: Pick<StockData, 'code' | 'market'>): boolean {
  if (stock.market) return stock.market === 'US';
  return usTickerFromCode(stock.code) !== null;
}

function canonicalUsSymbol(code: string, explicitUs = false): string | null {
  const ticker = usTickerFromCode(code, explicitUs);
  return ticker ? `us:${ticker}` : null;
}

export function applyLiveQuote(stock: StockData, quote: LiveQuote): StockData {
  if (!isUsInstrument(stock)) return stock;
  const stockSymbol = canonicalUsSymbol(stock.code, stock.market === 'US');
  const quoteSymbol = canonicalUsSymbol(quote.symbol, true);
  if (!stockSymbol || stockSymbol !== quoteSymbol) return stock;
  return { ...stock, liveQuote: quote };
}

export function currentPrice(stock: StockData): number | null {
  if (stock.liveQuote?.freshness === 'current') return stock.liveQuote.price;
  return stock.daily[stock.daily.length - 1]?.close ?? stock.indicators.lastClose ?? null;
}

export function buildLiveStreamUrl(baseUrl: string, codes: string[]): string {
  const tickers = codes
    .map((code) => usTickerFromCode(code, true))
    .filter((ticker): ticker is string => ticker !== null);
  if (tickers.length === 0) throw new Error('至少需要一个有效的美股代码');

  const url = new URL('/v1/stream', baseUrl);
  if (url.protocol === 'https:') url.protocol = 'wss:';
  else if (url.protocol === 'http:') url.protocol = 'ws:';
  else if (url.protocol !== 'ws:' && url.protocol !== 'wss:') {
    throw new Error(`不支持的实时行情 URL 协议：${url.protocol}`);
  }
  url.searchParams.set('symbols', [...new Set(tickers)].join(','));
  return url.toString();
}

export function liveStatusLabel(stock: StockData): string {
  const quote = stock.liveQuote;
  if (!quote) return '静态快照';
  if (quote.freshness === 'stale') return '实时数据已过期';
  if (quote.freshness === 'unknown') return '实时状态未知';
  if (quote.status === 'delayed') return 'Alpaca 延迟';
  return 'Alpaca 实时';
}
