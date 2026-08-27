import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyLiveQuote,
  buildLiveStreamUrl,
  currentPrice,
  isUsInstrument,
  liveStatusLabel,
} from './liveQuote.ts';

const stock = {
  code: 'AAPL.US',
  name: 'Apple',
  market: 'US',
  tradingStyle: 'Research',
  lastTradeDay: '2026-08-26',
  indicators: { lastClose: 200 },
  levels: [],
  daily: [
    { date: '2026-08-25', open: 198, high: 202, low: 197, close: 199, volume: 1 },
    { date: '2026-08-26', open: 199, high: 202, low: 198, close: 200, volume: 1 },
  ],
  intraday: null,
};

const quote = {
  symbol: 'us:AAPL',
  price: 201.25,
  timestamp: '2026-08-27T14:31:00+00:00',
  source: 'alpaca',
  status: 'live',
  freshness: 'current',
};

test('isUsInstrument supports metadata and decorated US symbols', () => {
  assert.equal(isUsInstrument(stock), true);
  assert.equal(isUsInstrument({ ...stock, market: undefined, code: 'us:MSFT' }), true);
  assert.equal(isUsInstrument({ ...stock, market: undefined, code: 'MSFT.US' }), true);
  assert.equal(isUsInstrument({ ...stock, market: 'CN', code: 'sz300246' }), false);
});

test('applyLiveQuote overlays a matching US quote without mutating historical bars', () => {
  const result = applyLiveQuote(stock, quote);

  assert.notEqual(result, stock);
  assert.deepEqual(result.daily, stock.daily);
  assert.equal(result.liveQuote?.price, 201.25);
  assert.equal(currentPrice(result), 201.25);
});

test('applyLiveQuote ignores a quote for another symbol', () => {
  const result = applyLiveQuote(stock, { ...quote, symbol: 'us:MSFT' });
  assert.equal(result, stock);
  assert.equal(currentPrice(result), 200);
});

test('buildLiveStreamUrl converts HTTP origins to websocket and uses provider tickers', () => {
  assert.equal(
    buildLiveStreamUrl('https://market.example.com/', ['AAPL.US', 'us:MSFT']),
    'wss://market.example.com/v1/stream?symbols=AAPL%2CMSFT',
  );
  assert.equal(
    buildLiveStreamUrl('http://127.0.0.1:8000', ['AAPL.US']),
    'ws://127.0.0.1:8000/v1/stream?symbols=AAPL',
  );
});

test('liveStatusLabel distinguishes current, stale, and static states', () => {
  assert.equal(liveStatusLabel({ ...stock, liveQuote: quote }), 'Alpaca 实时');
  assert.equal(liveStatusLabel({ ...stock, liveQuote: { ...quote, freshness: 'stale' } }), '实时数据已过期');
  assert.equal(liveStatusLabel(stock), '静态快照');
});
