import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildExportManifest,
  parseArgs,
  safeFileStem,
} from './export-charts.mjs';

test('parseArgs uses automation-friendly defaults', () => {
  const options = parseArgs([], {});

  assert.equal(options.url, null);
  assert.equal(options.theme, 'light');
  assert.equal(options.output, null);
});

test('parseArgs accepts URL, output directory and dark theme', () => {
  const options = parseArgs(
    [
      '--url',
      'https://example.com/dashboard/',
      '--output',
      '/tmp/charts',
      '--theme',
      'dark',
    ],
    {},
  );

  assert.equal(options.url, 'https://example.com/dashboard/');
  assert.equal(options.output, '/tmp/charts');
  assert.equal(options.theme, 'dark');
});

test('parseArgs reads automation settings from environment', () => {
  const options = parseArgs([], {
    DASHBOARD_EXPORT_URL: 'https://example.com/',
    DASHBOARD_EXPORT_DIR: '/tmp/from-env',
    DASHBOARD_EXPORT_THEME: 'dark',
  });

  assert.deepEqual(options, {
    url: 'https://example.com/',
    output: '/tmp/from-env',
    theme: 'dark',
  });
});

test('parseArgs rejects unsupported themes', () => {
  assert.throws(() => parseArgs(['--theme', 'system'], {}), /theme/);
});

test('safeFileStem removes path-sensitive characters', () => {
  assert.equal(safeFileStem('510050.SH'), '510050.SH');
  assert.equal(safeFileStem('a/b:c'), 'a_b_c');
});

test('buildExportManifest records stable machine-readable metadata', () => {
  const manifest = buildExportManifest({
    generatedAt: '2026-08-26',
    exportedAt: '2026-08-26T12:00:00.000Z',
    sourceUrl: 'https://example.com/',
    theme: 'light',
    images: [
      {
        kind: 'daily-chart',
        code: '510050.SH',
        name: '上证50ETF',
        file: '510050.SH-daily.png',
      },
    ],
  });

  assert.deepEqual(manifest, {
    schemaVersion: 'trading_research.chart_export.v1',
    generatedAt: '2026-08-26',
    exportedAt: '2026-08-26T12:00:00.000Z',
    sourceUrl: 'https://example.com/',
    theme: 'light',
    images: [
      {
        kind: 'daily-chart',
        code: '510050.SH',
        name: '上证50ETF',
        file: '510050.SH-daily.png',
      },
    ],
  });
});
