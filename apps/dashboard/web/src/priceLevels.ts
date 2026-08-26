import type { Level } from './types.ts';

export function distancePercent(
  current: number | null | undefined,
  level: number | null | undefined,
): number | null {
  if (current === null || current === undefined || level === null || level === undefined) {
    return null;
  }
  if (!Number.isFinite(current) || !Number.isFinite(level) || current === 0) return null;
  return (level - current) / current;
}
function nearestLevel(
  levels: Level[],
  type: Level['type'],
  current: number | null,
): Level | undefined {
  const candidates = levels.filter((level) => level.type === type);
  if (candidates.length === 0) return undefined;
  return [...candidates].sort((left, right) => {
    if (current === null) return 0;
    return Math.abs(left.value - current) - Math.abs(right.value - current);
  })[0];
}

export function visibleLevels(levels: Level[], current: number | null, showAll: boolean): Level[] {
  if (showAll || levels.length === 0) return levels;

  const selected = [
    nearestLevel(levels, 'support', current),
    nearestLevel(levels, 'resistance', current),
    nearestLevel(levels, 'key', current),
    nearestLevel(levels, 'center', current),
  ].filter((level): level is Level => level !== undefined);
  const selectedKeys = new Set(selected.map((level) => `${level.type}:${level.value}`));

  return levels.filter((level) => selectedKeys.has(`${level.type}:${level.value}`));
}

export function formatDistancePercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—';
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}
