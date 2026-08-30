import assert from 'node:assert/strict';
import test from 'node:test';

import { parseContextualResearch, selectContextualResearch } from './contextualResearch.ts';

function snapshot() {
  return {
    schemaVersion: 'trading_research.contextual_snapshot.v1',
    generatedAt: '2026-08-28',
    dataDate: '2026-08-28',
    quality: { status: 'pass', warnings: [] },
    coverage: { requested: 1, evaluated: 1, skipped: 0 },
    contexts: [
      {
        schemaVersion: 'trading_research.market_context.v1',
        instrument: { code: 'TSLA.US', name: 'TSLA' },
        dataDate: '2026-08-28',
        market: 'US',
        timezone: 'America/New_York',
        currentPrice: 220,
        referenceLevels: [],
        sessions: [],
        higherTimeframe: { trend20: 'up', return20: 0.08, rangePosition20: 0.82 },
        dayArchetype: { id: 'range', reasons: ['fixture'] },
        features: { rangeToAtr: 0.8, closeLocation: 0.5, intradayRangePct: 0.01 },
        intermarket: [],
        provenance: { source: 'fixture', definitionVersion: 'v1' },
      },
    ],
    setupEvents: [
      {
        schemaVersion: 'trading_research.setup_event.v1',
        instrument: 'TSLA.US',
        dataDate: '2026-08-28',
        timestamp: '2026-08-28 10:00:00',
        session: 'opening_range',
        eventType: 'cross_above',
        referenceLevel: { kind: 'previous_day_high', value: 219, sourceLabel: '前一日高点' },
        observedPrice: 220,
        tolerance: 0.1,
        outcome: { return5m: 0.01, return15m: null, return30m: null, mfe30m: 0.02, mae30m: -0.01 },
        definitionVersion: 'setup-detector.v1',
        provenance: { source: 'fixture' },
      },
    ],
    eventStudies: [],
    provenance: { source: 'fixture', definitionVersion: 'v1' },
  };
}

test('parses a supported contextual snapshot', () => {
  const parsed = parseContextualResearch(snapshot());
  assert.equal(parsed?.contexts[0].instrument.code, 'TSLA.US');
  assert.equal(parsed?.contexts[0].higherTimeframe.trend20, 'up');
});

test('unsupported version degrades to null', () => {
  const value = snapshot();
  value.schemaVersion = 'trading_research.contextual_snapshot.v99';
  assert.equal(parseContextualResearch(value), null);
});

test('malformed nested context degrades to null', () => {
  const value = snapshot();
  delete value.contexts[0].instrument;
  assert.equal(parseContextualResearch(value), null);
});

test('context without higher timeframe block degrades to null', () => {
  const value = snapshot();
  delete value.contexts[0].higherTimeframe;
  assert.equal(parseContextualResearch(value), null);
});

test('absent contextual research is allowed', () => {
  assert.equal(parseContextualResearch(undefined), null);
});

test('selection never leaks setup events across instruments', () => {
  const parsed = parseContextualResearch(snapshot());
  const tsla = selectContextualResearch(parsed, 'TSLA.US');
  const other = selectContextualResearch(parsed, 'AAPL.US');
  assert.equal(tsla.context?.instrument.code, 'TSLA.US');
  assert.equal(tsla.setupEvents.length, 1);
  assert.equal(other.context, null);
  assert.equal(other.setupEvents.length, 0);
});
