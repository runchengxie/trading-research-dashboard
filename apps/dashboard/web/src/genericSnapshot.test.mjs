import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { adaptNiuMenSnapshot } from './research/niuMenAdapter.ts';
import { parseResearchSnapshot } from './researchSnapshot.ts';
import { parseStrategyEnvelope, envelopeToStrategySnapshot } from './research/genericSnapshot.ts';
import { STRATEGY_DEFINITIONS } from './research/strategyRegistry.ts';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const V2_FIXTURE = path.join(
  REPO_ROOT,
  'packages/research-core/tests/fixtures/research_snapshot/valid_v2.json',
);
const GENERIC_FIXTURE = path.join(
  REPO_ROOT,
  'packages/research-core/tests/fixtures/strategy_snapshot/niu_men_generic_v1.json',
);
const RBREAKER_PUBLIC = path.join(REPO_ROOT, 'apps/dashboard/web/public/rbreaker-research.json');
const ICT_RECLAIM_PUBLIC = path.join(
  REPO_ROOT,
  'apps/dashboard/web/public/ict-liquidity-reclaim-research.json',
);

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const DASHBOARD_DATE = '2026-08-26';

test('generic envelope renders the Niu Men v2 fixture identically to the legacy adapter', () => {
  const v2 = readJson(V2_FIXTURE);
  const legacy = adaptNiuMenSnapshot(parseResearchSnapshot(v2), DASHBOARD_DATE);

  const envelope = parseStrategyEnvelope(readJson(GENERIC_FIXTURE));
  const generic = envelopeToStrategySnapshot(envelope, DASHBOARD_DATE);
  const rendered = {
    ...generic,
    details: adaptNiuMenSnapshot(parseResearchSnapshot(envelope.source.payload), DASHBOARD_DATE)
      .details,
  };

  assert.deepEqual(rendered, legacy);
});

test('registry resolves the committed adapted fixture through the generic model', () => {
  const definition = STRATEGY_DEFINITIONS.find((entry) => entry.id === 'niu-men-line');
  const snapshot = definition.adapt(readJson(GENERIC_FIXTURE), DASHBOARD_DATE);
  assert.equal(snapshot.strategyId, 'niu-men-line');
  assert.equal(snapshot.schemaVersion, 'niu_men.research_snapshot.v2');
  assert.equal(snapshot.coverage.requested, 3);
  assert.ok(snapshot.details.length > 0);
});

test('generic Niu Men snapshots preserve fold calendar metadata', () => {
  const payload = readJson(GENERIC_FIXTURE);
  const envelope = parseStrategyEnvelope(payload);
  const summary = envelopeToStrategySnapshot(envelope, DASHBOARD_DATE).rollingSummaries[0];
  assert.equal(summary.calendar.mode, 'range');
  assert.equal(summary.calendar.startDateMin, '2019-03-01');
  assert.equal(summary.calendar.endDateMax, '2021-02-28');
});

test('legacy v2 research.json remains consumable through the registry', () => {
  const definition = STRATEGY_DEFINITIONS.find((entry) => entry.id === 'niu-men-line');
  const snapshot = definition.adapt(readJson(V2_FIXTURE), DASHBOARD_DATE);
  assert.equal(snapshot.quality, 'pass');
  assert.equal(snapshot.variants.length, 6);
});

test('R-Breaker snapshot resolves through the registry', () => {
  const definition = STRATEGY_DEFINITIONS.find((entry) => entry.id === 'r-breaker');
  const payload = readJson(RBREAKER_PUBLIC);
  const snapshot = definition.adapt(payload, DASHBOARD_DATE);

  assert.equal(snapshot.strategyId, 'r-breaker');
  assert.equal(snapshot.strategyLabel, 'R-Breaker');
  assert.ok(snapshot.variants.length >= 1);
  assert.ok(snapshot.rollingSummaries.length >= 1);
  assert.match(snapshot.rollingSummaries[0].startDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(snapshot.rollingSummaries[0].endDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(snapshot.freshness, 'current');
  assert.deepEqual(snapshot.details.map((group) => group.id), ['execution']);
});

test('ICT liquidity reclaim snapshot resolves through the registry', () => {
  const definition = STRATEGY_DEFINITIONS.find((entry) => entry.id === 'ict-liquidity-reclaim');
  const snapshot = definition.adapt(readJson(ICT_RECLAIM_PUBLIC), DASHBOARD_DATE);

  assert.equal(snapshot.strategyId, 'ict-liquidity-reclaim');
  assert.equal(snapshot.quality, 'warning');
  assert.equal(snapshot.variants[0].id, 'ict_liquidity_reclaim_v1');
  assert.match(snapshot.rollingSummaries[0].startDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(snapshot.rollingSummaries[0].endDate, /^\d{4}-\d{2}-\d{2}$/);
  assert.ok(snapshot.details.some((group) => group.id === 'rule'));
});

test('rolling summary labels prefer concrete dates over ordinal windows', async () => {
  const { rollingSummaryLabel } = await import('./research/rollingLabels.ts');
  assert.equal(
    rollingSummaryLabel({ foldId: 0, startDate: '2026-08-01', endDate: '2026-08-31' }),
    '2026-08-01 → 2026-08-31',
  );
  assert.equal(
    rollingSummaryLabel({
      foldId: 0,
      calendar: {
        mode: 'range',
        startDateMin: '2019-03-01',
        endDateMax: '2021-02-28',
        datedSymbols: 3500,
        totalSymbols: 3808,
        distinctDatePairs: 12,
      },
    }),
    '2019-03-01 → 2021-02-28（个股日期范围）',
  );
  assert.equal(rollingSummaryLabel({ foldId: 1 }), '窗口 2');
});

test('unsupported generic versions fail clearly', () => {
  const payload = readJson(GENERIC_FIXTURE);
  payload.schemaVersion = 'trading_research.strategy_snapshot.v99';
  assert.throws(
    () => parseStrategyEnvelope(payload),
    /不支持的通用策略快照版本：trading_research\.strategy_snapshot\.v99/,
  );
});
