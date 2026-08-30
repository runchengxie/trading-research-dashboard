import type { StrategySnapshot, StrategyVariant } from './strategySnapshot.ts';

const DEFAULT_VARIANT_IDS: Record<string, string> = {
  'niu-men-line': 'nml_baseline',
  'r-breaker': 'rb_default',
  'ict-liquidity-reclaim': 'ict_liquidity_reclaim_v1',
};

export function defaultVariantFor(
  snapshot: Pick<StrategySnapshot, 'strategyId' | 'variants'>,
): StrategyVariant | null {
  const variantId = DEFAULT_VARIANT_IDS[snapshot.strategyId];
  return snapshot.variants.find((variant) => variant.id === variantId) ?? null;
}
