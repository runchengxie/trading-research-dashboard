import type { LiveQuote } from './types.ts';

export interface MarketDataHealth {
  status: 'ok';
  collectorConfigured: boolean;
  liveDataConfigured: boolean;
}

export type MarketDataServiceStatus = 'static' | 'online' | 'unknown';

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function normalizeBaseUrl(baseUrl: string): string {
  const normalized = baseUrl.trim().replace(/\/+$/, '');
  if (!normalized) {
    throw new Error('Market data API base URL is required');
  }
  return normalized;
}

async function requestJson(url: string, fetchImpl: FetchLike): Promise<unknown> {
  const response = await fetchImpl(url);
  if (!response.ok) {
    throw new Error(`Market data API request failed: HTTP ${response.status}`);
  }
  return response.json();
}

function isMarketDataHealth(value: unknown): value is MarketDataHealth {
  if (typeof value !== 'object' || value === null) return false;
  const health = value as Partial<MarketDataHealth>;
  return (
    health.status === 'ok' &&
    typeof health.collectorConfigured === 'boolean' &&
    typeof health.liveDataConfigured === 'boolean'
  );
}

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

export function marketDataServiceStatusLabel(status: MarketDataServiceStatus): string {
  if (status === 'online') return '行情服务在线';
  if (status === 'unknown') return '静态快照 · 行情服务状态未知';
  return '静态快照';
}

export async function fetchMarketDataHealth(
  baseUrl: string,
  fetchImpl: FetchLike = fetch,
): Promise<MarketDataHealth> {
  const value = await requestJson(`${normalizeBaseUrl(baseUrl)}/healthz`, fetchImpl);
  if (!isMarketDataHealth(value)) {
    throw new Error('Invalid market data health payload');
  }
  return value;
}

export async function fetchMarketDataQuote(
  baseUrl: string,
  symbol: string,
  fetchImpl: FetchLike = fetch,
): Promise<LiveQuote> {
  const value = await requestJson(
    `${normalizeBaseUrl(baseUrl)}/v1/quotes/${encodeURIComponent(symbol)}`,
    fetchImpl,
  );
  if (!isLiveQuote(value)) {
    throw new Error('Invalid market data quote payload');
  }
  return value;
}
