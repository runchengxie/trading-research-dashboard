import assert from 'node:assert/strict';
import test from 'node:test';

import {
  distancePercent,
  formatDistancePercent,
  visibleLevels,
} from './priceLevels.ts';

const levels = [
  { type: 'support', value: 98, label: '远支撑' },
  { type: 'support', value: 99, label: '最近支撑' },
  { type: 'resistance', value: 101, label: '最近阻力' },
  { type: 'resistance', value: 105, label: '远阻力' },
  { type: 'center', value: 100, label: '中枢' },
];

test('distancePercent measures the level relative to current price', () => {
  assert.equal(distancePercent(100, 98), -0.02);
  assert.equal(distancePercent(100, 101), 0.01);
  assert.equal(distancePercent(null, 101), null);
});

test('visibleLevels keeps nearest actionable levels by default', () => {
  assert.deepEqual(
    visibleLevels(levels, 100, false).map((level) => level.label),
    ['最近支撑', '最近阻力', '中枢'],
  );
});

test('visibleLevels returns all analytical levels when requested', () => {
  assert.equal(visibleLevels(levels, 100, true).length, levels.length);
});

test('formatDistancePercent uses a signed percentage', () => {
  assert.equal(formatDistancePercent(0.016), '+1.60%');
  assert.equal(formatDistancePercent(-0.02), '-2.00%');
  assert.equal(formatDistancePercent(null), '—');
});
