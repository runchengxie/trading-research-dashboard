import assert from 'node:assert/strict';
import test from 'node:test';

import { defaultVariantFor } from './research/defaultVariants.ts';

test('default variant mapping exposes one comparable overview row per strategy', () => {
  const snapshots = [
    {
      strategyId: 'niu-men-line',
      variants: [{ id: 'nml_baseline' }],
    },
    {
      strategyId: 'r-breaker',
      variants: [{ id: 'rb_default' }],
    },
    {
      strategyId: 'ict-liquidity-reclaim',
      variants: [{ id: 'ict_liquidity_reclaim_v1' }],
    },
  ];

  assert.deepEqual(snapshots.map(defaultVariantFor).map((variant) => variant.id), [
    'nml_baseline',
    'rb_default',
    'ict_liquidity_reclaim_v1',
  ]);
});

test('default variant mapping does not invent a row when the default is absent', () => {
  assert.equal(
    defaultVariantFor({ strategyId: 'r-breaker', variants: [{ id: 'other' }] }),
    null,
  );
});
