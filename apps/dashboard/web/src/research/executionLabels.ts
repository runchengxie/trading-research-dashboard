import type { ExecutionCapability } from '../types.ts';

export function formatExecutionConstraint(
  value: number | null,
  capability: ExecutionCapability,
): string {
  if (capability === 'not_modelled') return '未建模';
  if (capability === 'not_applicable') return '不适用';
  return value === null || Number.isNaN(value)
    ? '—'
    : Math.round(value).toLocaleString('zh-CN');
}
