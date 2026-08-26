import { parseResearchSnapshot } from '../researchSnapshot.ts';
import type { StrategySnapshot } from './strategySnapshot.ts';
import { adaptNiuMenSnapshot } from './niuMenAdapter.ts';

export type StrategyId = 'niu-men-line' | 'r-breaker';

export interface StrategyDefinition {
  id: StrategyId;
  label: string;
  description: string;
  snapshotPath: string;
  adapt: ((payload: unknown, dashboardDate: string) => StrategySnapshot) | null;
}

export const STRATEGY_DEFINITIONS: StrategyDefinition[] = [
  {
    id: 'niu-men-line',
    label: '牛门线',
    description: '全市场滚动样本外研究',
    snapshotPath: './research.json',
    adapt: (payload, dashboardDate) =>
      adaptNiuMenSnapshot(parseResearchSnapshot(payload), dashboardDate),
  },
  {
    id: 'r-breaker',
    label: 'R-Breaker',
    description: '日内突破与反转策略研究',
    snapshotPath: './rbreaker-research.json',
    adapt: null,
  },
];
