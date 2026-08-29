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

test('dark chart visuals separate the page grid from the chart surface', () => {
  const theme = read('theme.ts');
  const editorial = read('editorial.css');

  assert.match(theme, /gridColor:\s*'rgba\(155, 175, 195, 0\.13\)'/);
  assert.match(theme, /minorGridColor:\s*'rgba\(155, 175, 195, 0\.045\)'/);
  assert.match(editorial, /--chart-surface:\s*#151b21/);
  assert.match(editorial, /--editorial-grid:\s*rgba\(175, 190, 205, 0\.02\)/);
});

test('dashboard exposes one-page market switching for CN, HK and US', () => {
  const source = read('App.tsx');
  assert.match(source, /市场筛选/);
  assert.match(source, /全部市场/);
  assert.match(source, /美股/);
  assert.match(source, /const filteredStocks = data\.stocks\.filter/);
  assert.match(source, /activeMarket === 'ALL'/);
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

test('research panel distinguishes single backtests and ordinal rolling windows', () => {
  const source = read('components/ResearchPanel.tsx');
  assert.match(source, /单标的单次回测/);
  assert.match(source, /按标的序号/);
  assert.match(source, /滚动窗口（按标的序号）/);
});
