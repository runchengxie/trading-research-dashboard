import assert from 'node:assert/strict';
import test from 'node:test';

import { primaryIndicatorRows } from './research/primaryIndicators.ts';

test('primary indicator rows expose VWAP and both ORB boundaries', () => {
  assert.deepEqual(
    primaryIndicatorRows({ vwap: 15.1, orbHigh: 15.4, orbLow: 14.9 }),
    [
      { key: 'vwap', label: 'VWAP', value: 15.1 },
      { key: 'orbHigh', label: 'ORB突破上轨', value: 15.4 },
      { key: 'orbLow', label: 'ORB突破下轨', value: 14.9 },
    ],
  );
});
