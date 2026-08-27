import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

test('chart palettes use the editorial research axis and line colors', () => {
  const source = readFileSync(join(here, 'theme.ts'), 'utf8');

  assert.match(source, /axisLineColor: '#9ba3ab'/);
  assert.match(source, /axisLabelColor: '#5f6872'/);
  assert.match(source, /tooltipBg: '#232a33'/);
  assert.match(source, /lineColor: '#1267d6'/);
  assert.match(source, /axisLineColor: '#66717d'/);
  assert.match(source, /lineColor: '#66a8ff'/);
});
