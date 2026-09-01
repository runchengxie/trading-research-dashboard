import assert from 'node:assert/strict';
import test from 'node:test';

import {
  fetchMarketDataHealth,
  fetchMarketDataQuote,
  marketDataServiceStatusLabel,
} from './marketDataApi.ts';

test('health client removes trailing slash before requesting healthz', async () => {
  let requested = '';
  const fetchImpl = async (url) => {
    requested = String(url);
    return new Response(
      JSON.stringify({
        status: 'ok',
        collectorConfigured: true,
        liveDataConfigured: true,
      }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  };

  const result = await fetchMarketDataHealth('https://market.example/', fetchImpl);

  assert.equal(requested, 'https://market.example/healthz');
  assert.equal(result.liveDataConfigured, true);
});

test('quote client URL-encodes the symbol', async () => {
  let requested = '';
  const fetchImpl = async (url) => {
    requested = String(url);
    return new Response(
      JSON.stringify({
        symbol: 'us:AAPL',
        price: 200,
        timestamp: '2026-09-01T00:00:00+00:00',
        source: 'test',
        status: 'live',
        freshness: 'current',
      }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  };

  await fetchMarketDataQuote('https://market.example', 'AAPL/US', fetchImpl);

  assert.equal(requested, 'https://market.example/v1/quotes/AAPL%2FUS');
});

test('health client rejects malformed payloads', async () => {
  const fetchImpl = async () =>
    new Response(JSON.stringify({ status: 'ok' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });

  await assert.rejects(
    fetchMarketDataHealth('https://market.example', fetchImpl),
    /invalid market data health payload/i,
  );
});

test('quote client surfaces HTTP status', async () => {
  const fetchImpl = async () => new Response('missing', { status: 404 });

  await assert.rejects(
    fetchMarketDataQuote('https://market.example', 'MSFT.US', fetchImpl),
    /market data API request failed: HTTP 404/i,
  );
});

test('service status labels distinguish verified and unverified modes', () => {
  assert.equal(marketDataServiceStatusLabel('online'), '行情服务在线');
  assert.equal(marketDataServiceStatusLabel('static'), '静态快照');
  assert.equal(
    marketDataServiceStatusLabel('unknown'),
    '静态快照 · 行情服务状态未知',
  );
});
