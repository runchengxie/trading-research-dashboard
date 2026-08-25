import type { ResearchFreshness } from '../researchSnapshot';

export interface StrategyVariant {
  id: string;
  label: string;
  symbols: number;
  foldRows: number;
  annualizedReturnMedian: number | null;
  sharpeMedian: number | null;
  maxDrawdownMedian: number | null;
  tradeCountMedian: number | null;
  winRateMedian: number | null;
  profitFactorMedian: number | null;
  entrySignalCount: number | null;
  blockedEntryCount: number | null;
  blockedExitDayCount: number | null;
  sectorRetreatBlockCount: number | null;
  priceRegimeBlockCount: number | null;
}

export interface StrategyRollingSummary {
  variant: string;
  foldId: number;
  symbols: number;
  annualizedReturnMedian: number | null;
  sharpeMedian: number | null;
  maxDrawdownMedian: number | null;
  tradeCountMedian: number | null;
  winRateMedian: number | null;
  profitFactorMedian: number | null;
  entrySignalCount: number | null;
  sectorRetreatBlockCount: number | null;
  priceRegimeBlockCount: number | null;
}

export interface StrategyProvenance {
  researchCommit: string | null;
  dataPlatform: string;
  dataPlatformSchemaVersion: string | null;
  dataPlatformGeneratedAt: string | null;
  oosSchemaVersion: string;
  oosGeneratedAt: string | null;
}

export interface StrategyDetailItem {
  label: string;
  value: string;
}

export interface StrategyDetailGroup {
  id: string;
  label: string;
  items: StrategyDetailItem[];
}

export interface StrategySnapshot {
  strategyId: string;
  strategyLabel: string;
  schemaVersion: string;
  generatedAt: string;
  dataDate: string;
  freshness: ResearchFreshness;
  quality: 'pass' | 'warning';
  coverage: {
    requested: number;
    evaluated: number;
    skipped: number;
  };
  variants: StrategyVariant[];
  rollingSummaries: StrategyRollingSummary[];
  walkForward: {
    trainBars: number;
    testBars: number;
    stepBars: number;
    semantics: string;
  };
  executionTiming: string;
  provenance: StrategyProvenance;
  details: StrategyDetailGroup[];
}

