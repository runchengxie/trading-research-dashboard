export type ComparisonMetricStatus = 'value' | 'not_provided' | 'not_shared';
export type ComparisonMetricKind = 'percent' | 'number';

export function formatComparisonMetric(
  value: number | null,
  status: ComparisonMetricStatus,
  kind: ComparisonMetricKind,
  digits = kind === 'percent' ? 2 : 3,
): string {
  if (status === 'not_shared') return '无共同变体';
  if (status === 'not_provided' || value === null || Number.isNaN(value)) return '未提供';
  return kind === 'percent'
    ? `${(value * 100).toFixed(digits)}%`
    : value.toFixed(digits);
}
