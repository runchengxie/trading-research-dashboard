import assert from 'node:assert/strict';
import test from 'node:test';

import { parseResearchSnapshot, researchFreshness } from './researchSnapshot.ts';

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
    variants: [],
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

test('研究快照 v1 在迁移期继续可读', () => {
  const snapshot = parseResearchSnapshot(baseSnapshot());
  assert.equal(snapshot.schemaVersion, 'niu_men.research_snapshot.v1');
  assert.equal(snapshot.source.dataDate, '2026-08-24');
});

test('研究快照 v2 要求完整 provenance 结构', () => {
  const payload = baseSnapshot('niu_men.research_snapshot.v2');
  payload.generatedAt = '2026-08-25T10:15:00Z';
  Object.assign(payload.source, {
    researchCommit: 'a'.repeat(40),
    oosGeneratedAt: '2026-08-25',
    dataPlatformManifest: {
      schemaVersion: 'niu_men.etf_industry_context_manifest.v1',
      generatedAt: '2026-08-25',
    },
  });
  payload.quality.checks.provenanceComplete = true;

  const snapshot = parseResearchSnapshot(payload);

  assert.equal(snapshot.schemaVersion, 'niu_men.research_snapshot.v2');
  assert.equal(snapshot.source.researchCommit, 'a'.repeat(40));
});

test('研究快照 v2 缺少 provenance 时拒绝加载', () => {
  const payload = baseSnapshot('niu_men.research_snapshot.v2');

  assert.throws(() => parseResearchSnapshot(payload), /v2 来源信息不完整/);
});

test('未知研究快照版本明确报错', () => {
  const payload = baseSnapshot('niu_men.research_snapshot.v9');

  assert.throws(() => parseResearchSnapshot(payload), /不支持的研究快照版本/);
});

test('同日或更晚研究数据视为当前', () => {
  assert.equal(researchFreshness('2026-08-24', '2026-08-24'), 'current');
  assert.equal(researchFreshness('2026-08-24', '2026-08-25'), 'current');
});

test('研究数据早于行情日期时视为过期', () => {
  assert.equal(researchFreshness('2026-08-25', '2026-08-24'), 'stale');
});

test('日期格式不可判断时不制造过期结论', () => {
  assert.equal(researchFreshness('2026/08/25', '2026-08-24'), 'unknown');
  assert.equal(researchFreshness('2026-08-25', ''), 'unknown');
});
