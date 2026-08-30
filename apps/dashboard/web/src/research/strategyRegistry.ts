import { parseResearchSnapshot } from '../researchSnapshot.ts';
import type { StrategySnapshot } from './strategySnapshot.ts';
import {
  GENERIC_SNAPSHOT_VERSION,
  envelopeToStrategySnapshot,
  parseStrategyEnvelope,
} from './genericSnapshot.ts';
import { adaptNiuMenSnapshot, detailGroups } from './niuMenAdapter.ts';

export type StrategyId = 'niu-men-line' | 'r-breaker' | 'ict-liquidity-reclaim';

export interface StrategyDefinition {
  id: StrategyId;
  label: string;
  description: string;
  snapshotPath: string;
  adapt: (payload: unknown, dashboardDate: string) => StrategySnapshot;
}

function isGenericEnvelope(payload: unknown): boolean {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    (payload as { schemaVersion?: unknown }).schemaVersion === GENERIC_SNAPSHOT_VERSION
  );
}

function adaptNiuMenPayload(payload: unknown, dashboardDate: string): StrategySnapshot {
  if (isGenericEnvelope(payload)) {
    const envelope = parseStrategyEnvelope(payload);
    const snapshot = envelopeToStrategySnapshot(envelope, dashboardDate);
    const source = envelope.source;
    if (source && source.wireVersion.startsWith('niu_men.research_snapshot.')) {
      return { ...snapshot, details: detailGroups(parseResearchSnapshot(source.payload)) };
    }
    return snapshot;
  }
  return adaptNiuMenSnapshot(parseResearchSnapshot(payload), dashboardDate);
}

function adaptRBreakerPayload(payload: unknown, dashboardDate: string): StrategySnapshot {
  const envelope = parseStrategyEnvelope(payload);
  return envelopeToStrategySnapshot(envelope, dashboardDate);
}

export const STRATEGY_DEFINITIONS: StrategyDefinition[] = [
  {
    id: 'niu-men-line',
    label: '牛门线',
    description: '全市场滚动样本外研究',
    snapshotPath: './research.json',
    adapt: adaptNiuMenPayload,
  },
  {
    id: 'r-breaker',
    label: 'R-Breaker',
    description: '日内突破与反转策略研究',
    snapshotPath: './rbreaker-research.json',
    adapt: adaptRBreakerPayload,
  },
  {
    id: 'ict-liquidity-reclaim',
    label: 'ICT 流动性回收',
    description: 'PDH/PDL sweep + reclaim 的客观日内研究',
    snapshotPath: './ict-liquidity-reclaim-research.json',
    adapt: adaptRBreakerPayload,
  },
];
