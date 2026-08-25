import assert from 'node:assert/strict';
import test from 'node:test';

import {
  parseResearchSnapshot,
  researchFreshness,
  snapshotFreshness,
} from './researchSnapshot.ts';
import { adaptNiuMenSnapshot } from './research/niuMenAdapter.ts';
import { loadStrategySnapshot } from './api.ts';
import { STRATEGY_DEFINITIONS } from './research/strategyRegistry.ts';

const VARIANTS = [
  'nml_baseline',
  'nml_no_price_volume_filters',
  'simple_20_day_breakout',
  'nml_simple_trend_gate',
  'nml_sector_retreat',
  'buy_and_hold',
];

function variant(id) {
  return {
    id,
    label: id,
    symbols: 2,
    foldRows: 2,
    annualizedReturnMedian: 0.01,
    sharpeMedian: 0.1,
    maxDrawdownMedian: -0.1,
    tradeCountMedian: 2,
    winRateMedian: 0.5,
    profitFactorMedian: 1.1,
    entrySignalCount: 2,
    blockedEntryCount: 0,
    blockedExitDayCount: 0,
    sectorRetreatBlockCount: 0,
    priceRegimeBlockCount: 0,
  };
}

function baseSnapshot(schemaVersion = 'niu_men.research_snapshot.v1') {
  return {
    schemaVersion,
    generatedAt: '2026-08-25',
    source: {
      researchEngine: 'niu-men-line-strategy',
      dataPlatform: 'market-data-platform',
      dataDate: '2026-08-24',
      oosSchemaVersion: 'niu_men.industry_context_oos_full_market.v2',
      assets: {
        stockPool: 'pool.csv',
        industryChanges: 'changes.parquet',
        industryAudit: 'audit.csv',
        industryContext: 'context.parquet',
        dailyCleanRoot: 'daily',
        folds: 'folds.csv',
        summary: 'summary.csv',
        skips: 'skips.csv',
      },
    },
    mapping: {
      confidence: 'expanded',
      mappedIndustryCodes: 10,
      mappedProxyIndustryCodes: 5,
      coverage: { industryRowCoverage: 0.8, symbolCoverage: 0.9 },
    },
    coverage: {
      requestedSymbols: 2,
      evaluatedSymbols: 2,
      skippedSymbols: 0,
      skipReasons: {},
      contextWarmup: {
        rule: 'sector_ma60 is non-null',
        minBars: 1008,
        skippedSymbols: 0,
        contextRows: 100,
        readyRows: 80,
        warmupRows: 20,
      },
    },
    walkForward: {
      trainBars: 756,
      testBars: 252,
      stepBars: 252,
      foldSemantics: 'ordinal',
      summaries: [],
    },
    variants: VARIANTS.map(variant),
    executionConstraints: { timing: 'next open', byVariant: {} },
    quality: {
      status: 'pass',
      checks: {
        coverageCountsReconcile: true,
        expectedVariantsPresent: true,
        foldKeysUnique: true,
        oosRowsPresent: true,
      },
      duplicateFoldRows: 0,
    },
  };
}

function v2Snapshot({ provenanceComplete = true } = {}) {
  const payload = baseSnapshot('niu_men.research_snapshot.v2');
  payload.generatedAt = '2026-08-25T10:15:00Z';
  Object.assign(payload.source, {
    researchCommit: provenanceComplete ? 'a'.repeat(40) : null,
    oosGeneratedAt: '2026-08-25',
    dataPlatformManifest: {
      schemaVersion: provenanceComplete
        ? 'niu_men.etf_industry_context_manifest.v1'
        : null,
      generatedAt: provenanceComplete ? '2026-08-25' : null,
    },
  });
  payload.quality.checks.provenanceComplete = provenanceComplete;
  payload.quality.status = provenanceComplete ? 'pass' : 'warning';
  return payload;
}

test('研究快照 v1 在迁移期继续可读', () => {
  const snapshot = parseResearchSnapshot(baseSnapshot());
  assert.equal(snapshot.schemaVersion, 'niu_men.research_snapshot.v1');
  assert.equal(snapshot.source.dataDate, '2026-08-24');
});

test('研究快照 v1 保留 schema 允许的空说明字符串', () => {
  const payload = baseSnapshot();
  payload.coverage.contextWarmup.rule = '';
  payload.walkForward.foldSemantics = '';
  payload.executionConstraints.timing = '';

  assert.doesNotThrow(() => parseResearchSnapshot(payload));
});

test('研究快照 v2 要求完整 provenance 结构', () => {
  const snapshot = parseResearchSnapshot(v2Snapshot());

  assert.equal(snapshot.schemaVersion, 'niu_men.research_snapshot.v2');
  assert.equal(snapshot.source.researchCommit, 'a'.repeat(40));
});

test('研究快照 v2 缺少 provenance 结构时拒绝加载', () => {
  const payload = baseSnapshot('niu_men.research_snapshot.v2');

  assert.throws(() => parseResearchSnapshot(payload), /v2 来源信息不完整/);
});

test('未知研究快照版本明确报错', () => {
  const payload = baseSnapshot('niu_men.research_snapshot.v9');

  assert.throws(() => parseResearchSnapshot(payload), /不支持的研究快照版本/);
});

test('少于六个策略变体时拒绝加载', () => {
  const payload = baseSnapshot();
  payload.variants = payload.variants.slice(0, 5);

  assert.throws(() => parseResearchSnapshot(payload), /variants 至少需要 6 项/);
});

test('同日或更晚研究数据视为当前', () => {
  assert.equal(researchFreshness('2026-08-24', '2026-08-24'), 'current');
  assert.equal(researchFreshness('2026-08-24', '2026-08-25'), 'current');
});

test('研究数据早于行情日期时视为过期', () => {
  assert.equal(researchFreshness('2026-08-25', '2026-08-24'), 'stale');
});

test('日期格式或日历日期不可判断时不制造过期结论', () => {
  assert.equal(researchFreshness('2026/08/25', '2026-08-24'), 'unknown');
  assert.equal(researchFreshness('2026-08-25', ''), 'unknown');
  assert.equal(researchFreshness('2026-13-40', '2026-08-24'), 'unknown');
});

test('v2 provenance 明确不完整时新鲜度保持未知', () => {
  const snapshot = parseResearchSnapshot(v2Snapshot({ provenanceComplete: false }));

  assert.equal(snapshotFreshness('2026-08-24', snapshot), 'unknown');
});

test('Niu Men v2 snapshot adapts to the common strategy model', () => {
  const snapshot = parseResearchSnapshot(v2Snapshot());
  const normalized = adaptNiuMenSnapshot(snapshot, '2026-08-24');

  assert.equal(normalized.strategyId, 'niu-men-line');
  assert.equal(normalized.strategyLabel, '牛门线');
  assert.equal(normalized.schemaVersion, 'niu_men.research_snapshot.v2');
  assert.equal(normalized.freshness, 'current');
  assert.equal(normalized.quality, 'pass');
  assert.deepEqual(normalized.coverage, { requested: 2, evaluated: 2, skipped: 0 });
  assert.equal(normalized.variants.length, 6);
  assert.equal(normalized.rollingSummaries.length, 0);
  assert.equal(normalized.provenance.researchCommit, 'a'.repeat(40));
  assert.equal(normalized.details.some((group) => group.id === 'quality'), true);
});

test('Niu Men v1 snapshot remains normalized with unknown provenance', () => {
  const snapshot = parseResearchSnapshot(baseSnapshot());
  const normalized = adaptNiuMenSnapshot(snapshot, '2026-08-24');

  assert.equal(normalized.freshness, 'current');
  assert.equal(normalized.provenance.researchCommit, null);
  assert.equal(normalized.details.some((group) => group.id === 'coverage'), true);
});

test('strategy loader treats a missing snapshot as a local missing state', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response('', { status: 404 });

  try {
    const result = await loadStrategySnapshot(STRATEGY_DEFINITIONS[1], '2026-08-25');
    assert.equal(result.status, 'missing');
    assert.equal(result.snapshot, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('strategy loader localizes unsupported snapshot errors', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(
    JSON.stringify({ schemaVersion: 'niu_men.research_snapshot.v999' }),
    { status: 200, headers: { 'content-type': 'application/json' } },
  );

  try {
    const result = await loadStrategySnapshot(STRATEGY_DEFINITIONS[0], '2026-08-25');
    assert.equal(result.status, 'error');
    assert.match(result.error ?? '', /不支持的研究快照版本/);
    assert.equal(result.snapshot, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
