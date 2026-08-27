import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const read = (name) => readFileSync(join(here, name), 'utf8');

test('chart palettes provide restrained major and minor grid colors', () => {
  const source = read('theme.ts');
  assert.match(source, /gridColor:\s*string/);
  assert.match(source, /minorGridColor:\s*string/);
  assert.match(source, /gridColor:\s*'#/g);
  assert.match(source, /minorGridColor:\s*'#/g);
});

test('daily chart exposes PNG export and the CLI hint', () => {
  const source = read('components/StockChart.tsx');
  assert.match(source, /导出 PNG/);
  assert.match(source, /npm run export:charts/);
  assert.match(source, /downloadChartImage/);
});

test('intraday chart exposes a PNG export action', () => {
  const source = read('components/IntradayChart.tsx');
  assert.match(source, /导出 PNG/);
  assert.match(source, /downloadChartImage/);
});

test('chart export uses the ECharts image API', () => {
  const source = read('chartExport.ts');
  assert.match(source, /getDataURL/);
  assert.match(source, /pixelRatio:\s*2/);
  assert.match(source, /download/);
});

test('chart export keeps controls subtle and keyboard-visible', () => {
  const source = read('styles.css');
  assert.match(source, /\.chart-export-button\s*\{/);
  assert.match(source, /\.chart-export-button:focus-visible/);
  assert.match(source, /\.chart-cli-hint\s*\{/);
});
