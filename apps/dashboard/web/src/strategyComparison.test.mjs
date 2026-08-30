import assert from 'node:assert/strict';
import test from 'node:test';

import { formatComparisonMetric } from './research/comparisonLabels.ts';

test('comparison cells distinguish values, missing metrics, and non-shared variants', () => {
  assert.equal(formatComparisonMetric(0.125, 'value', 'percent'), '12.50%');
  assert.equal(formatComparisonMetric(null, 'not_provided', 'number'), '未提供');
  assert.equal(formatComparisonMetric(null, 'not_shared', 'number'), '无共同变体');
  assert.equal(formatComparisonMetric(null, 'not_applicable', 'number'), '不适用');
});
