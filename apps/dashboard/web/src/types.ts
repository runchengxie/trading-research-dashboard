export interface DailyBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IntradayBar {
  time: string;
  price: number;
  volume: number;
}

export type LevelType = 'support' | 'resistance' | 'key' | 'center';

export interface Level {
  type: LevelType;
  value: number;
  label: string;
}

export interface IndicatorValues {
  lastClose: number | null;
  atr20: number | null;
  support: number | null;
  resistance: number | null;
  nearestKeyLevel: number | null;
  yesterdayLow: number | null;
  yesterdayHigh: number | null;
  vwap: number | null;
  vwapDev: number | null;
  vwapDevThreshold: number | null;
  orbHigh: number | null;
  orbLow: number | null;
}

export interface UsageNote {
  param: string;
  note: string;
}

export type Market = 'CN' | 'HK' | 'US';
export type Currency = 'CNY' | 'HKD' | 'USD';
export type QuoteStatus = 'live' | 'delayed';
export type QuoteFreshness = 'current' | 'stale' | 'unknown';

export interface LiveQuote {
  symbol: string;
  price: number;
  timestamp: string;
  source: string;
  status: QuoteStatus;
  freshness: QuoteFreshness;
}

export interface StockData {
  code: string;
  name: string;
  // 旧版仓库兜底 data.json 尚未包含这些迁移期字段，因此保持 optional。
  instrumentType?: 'stock' | 'etf';
  market?: Market;
  currency?: Currency;
  timezone?: string;
  liveQuote?: LiveQuote;
  tradingStyle: string;
  lastTradeDay: string;
  indicators: IndicatorValues;
  levels: Level[];
  daily: DailyBar[];
  intraday: IntradayBar[] | null;
  usageNotes?: UsageNote[];
}

export interface DashboardData {
  generatedAt: string;
  stocks: StockData[];
  contextualResearch?: unknown;
  conditionalResearch?: unknown;
}

export interface ResearchSourceAssets {
  stockPool: string | null;
  industryChanges: string | null;
  industryAudit: string | null;
  industryContext: string | null;
  dailyCleanRoot: string | null;
  folds: string | null;
  summary: string | null;
  skips: string | null;
}

export interface ResearchDataPlatformManifest {
  schemaVersion: string | null;
  generatedAt: string | null;
}

export interface ResearchVariant {
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

export interface ResearchRollingSummary {
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

export interface ResearchSnapshot {
  schemaVersion: 'niu_men.research_snapshot.v1' | 'niu_men.research_snapshot.v2';
  generatedAt: string;
  source: {
    researchEngine: 'niu-men-line-strategy';
    researchCommit?: string | null;
    dataPlatform: string;
    dataDate: string;
    dataPlatformManifest?: ResearchDataPlatformManifest;
    oosSchemaVersion: string;
    oosGeneratedAt?: string;
    assets: ResearchSourceAssets;
  };
  mapping: {
    confidence: 'expanded' | 'high';
    mappedIndustryCodes: number;
    mappedProxyIndustryCodes: number;
    coverage: {
      industryRowCoverage: number | null;
      symbolCoverage: number | null;
    };
  };
  coverage: {
    requestedSymbols: number;
    evaluatedSymbols: number;
    skippedSymbols: number;
    skipReasons: Record<string, number>;
    contextWarmup: {
      rule: string;
      minBars: number;
      skippedSymbols: number;
      contextRows: number | null;
      readyRows: number | null;
      warmupRows: number | null;
    };
  };
  walkForward: {
    trainBars: number;
    testBars: number;
    stepBars: number;
    foldSemantics: string;
    summaries: ResearchRollingSummary[];
  };
  variants: ResearchVariant[];
  executionConstraints: {
    timing: string;
    byVariant: Record<
      string,
      {
        blockedEntryCount: number;
        blockedExitDayCount: number;
      }
    >;
  };
  quality: {
    status: 'pass' | 'warning';
    checks: {
      coverageCountsReconcile: boolean;
      expectedVariantsPresent: boolean;
      foldKeysUnique: boolean;
      oosRowsPresent: boolean;
      provenanceComplete?: boolean;
    };
    duplicateFoldRows: number | null;
  };
}
