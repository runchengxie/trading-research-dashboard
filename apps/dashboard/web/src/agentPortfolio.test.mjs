import assert from 'node:assert/strict';
import test from 'node:test';

import { displayInstrument, parseAgentPortfolio } from './agentPortfolio.ts';

function validSnapshot() {
  return {
    schemaVersion: 'trading_research.agent_portfolio.v1',
    generatedAt: '2026-09-01T22:00:00Z',
    asOf: '2026-09-01',
    agent: {
      id: 'glm-daily',
      provider: 'zhipu',
      model: 'glm-4.7-flash',
      promptVersion: 'agent-paper-v1',
      inputHash: 'a'.repeat(64),
    },
    portfolio: {
      initialEquity: 100000,
      equity: 100000,
      cash: 100000,
      nav: 1,
      totalReturn: 0,
      maxDrawdown: 0,
    },
    metrics: { totalReturn: 0, maxDrawdown: 0 },
    decision: { targetWeights: { CASH: 1 }, reasoningSummary: '观望。' },
    positions: [],
    trades: [],
    history: [],
  };
}

test('loads a valid agent portfolio snapshot', () => {
  const snapshot = parseAgentPortfolio(validSnapshot());
  assert.equal(snapshot.schemaVersion, 'trading_research.agent_portfolio.v1');
  assert.equal(snapshot.portfolio.nav, 1);
});

test('rejects an unsupported agent portfolio version', () => {
  assert.throws(
    () => parseAgentPortfolio({ ...validSnapshot(), schemaVersion: 'v9' }),
    /不支持的 Agent 组合快照版本/,
  );
});

test('rejects non-finite portfolio metrics', () => {
  assert.throws(
    () => parseAgentPortfolio({ ...validSnapshot(), portfolio: { ...validSnapshot().portfolio, nav: NaN } }),
    /Agent 组合快照字段无效/,
  );
});

test('rejects malformed positions and agent metadata', () => {
  const snapshot = validSnapshot();
  snapshot.agent.inputHash = 'invalid';
  snapshot.positions = [{ symbol: 'SPY', shares: 1.5, price: 100, marketValue: 100, weight: 1 }];
  assert.throws(() => parseAgentPortfolio(snapshot), /Agent 组合快照字段无效/);
});

test('shows the Chinese name beside known A-share instruments', () => {
  assert.equal(displayInstrument('159915.SZ'), '159915.SZ · 创业板ETF');
  assert.equal(displayInstrument('510300.SH'), '510300.SH · 沪深300ETF');
  assert.equal(displayInstrument('UNKNOWN'), 'UNKNOWN');
});
