export interface ContextualReferenceLevel {
  kind: string;
  value: number;
  distancePct: number | null;
  sourceLabel: string;
}

export interface ContextualIntermarketObservation {
  peer: string;
  correlation20: number;
  relativeStrength20: number;
  extremeConfirmation: 'confirmed' | 'diverged' | 'unknown';
  relativeExtremeDivergence: boolean;
}

export interface ContextualMarketContext {
  schemaVersion: 'trading_research.market_context.v1';
  instrument: { code: string; name: string };
  dataDate: string;
  market: 'CN' | 'HK' | 'US';
  timezone: string;
  currentPrice: number | null;
  referenceLevels: ContextualReferenceLevel[];
  sessions: Array<{
    id: string;
    high: number;
    low: number;
    returnPct: number | null;
    bars: number;
  }>;
  higherTimeframe: {
    trend20: 'up' | 'down' | 'flat' | 'insufficient_data';
    return20: number | null;
    rangePosition20: number | null;
  };
  dayArchetype: { id: string; reasons: string[] };
  features: {
    rangeToAtr: number | null;
    closeLocation: number | null;
    intradayRangePct: number | null;
  };
  intermarket: ContextualIntermarketObservation[];
}

export interface ContextualSetupEvent {
  schemaVersion: 'trading_research.setup_event.v1';
  instrument: string;
  dataDate: string;
  timestamp: string;
  session: string | null;
  eventType: string;
  referenceLevel: { kind: string; value: number; sourceLabel: string };
  observedPrice: number;
  tolerance: number;
  outcome: {
    return5m: number | null;
    return15m: number | null;
    return30m: number | null;
    mfe30m: number | null;
    mae30m: number | null;
  };
  definitionVersion: string;
}

export interface ContextualEventStudy {
  schemaVersion: 'trading_research.event_study.v1';
  event: {
    id: string;
    category: string;
    importance: 'low' | 'medium' | 'high';
    timestamp: string;
  };
  instrument: string;
  dataDate: string;
  preWindowMinutes: number;
  postWindowMinutes: number;
  metrics: {
    preReturn: number | null;
    preRangePct: number | null;
    immediateRangePct: number | null;
    return15m: number | null;
    return30m: number | null;
    return60m: number | null;
    mfe60m: number | null;
    mae60m: number | null;
    initialMoveReversal: boolean | null;
  };
}

export interface ContextualResearchSnapshot {
  schemaVersion: 'trading_research.contextual_snapshot.v1';
  generatedAt: string;
  dataDate: string;
  quality: { status: 'pass' | 'warning'; warnings: string[] };
  coverage: { requested: number; evaluated: number; skipped: number };
  contexts: ContextualMarketContext[];
  setupEvents: ContextualSetupEvent[];
  eventStudies: ContextualEventStudy[];
}

export interface ConditionalResearchDimensions {
  instrument: string | null;
  market: 'CN' | 'HK' | 'US' | null;
  session: string | null;
  dayArchetype: string | null;
  eventType: string | null;
  referenceLevelKind: string | null;
  strategyId: string | null;
  variantId: string | null;
}

export interface ConditionalResearchMetrics {
  sampleCount: number;
  winRate: number | null;
  expectancy: number | null;
  meanReturn: number | null;
  meanMfe: number | null;
  meanMae: number | null;
  dateCount: number;
  instrumentCount: number;
}

export interface ConditionalResearchGroup {
  dimensions: ConditionalResearchDimensions;
  metrics: ConditionalResearchMetrics;
}

export interface ConditionalResearchSnapshot {
  schemaVersion: 'trading_research.conditional_research.v1';
  generatedAt: string;
  dateRange: { start: string; end: string };
  sourceSnapshots: number;
  quality: { status: 'pass' | 'warning'; warnings: string[] };
  coverage: {
    requestedSnapshots: number;
    evaluatedSnapshots: number;
    skippedSnapshots: number;
    setupSamples: number;
    strategySamples: number;
  };
  groups: ConditionalResearchGroup[];
  provenance: { source: string; definitionVersion: string };
}

export interface SelectedContextualResearch {
  context: ContextualMarketContext | null;
  setupEvents: ContextualSetupEvent[];
  eventStudies: ContextualEventStudy[];
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

function validContext(value: unknown): boolean {
  if (!isObject(value)) return false;
  if (value.schemaVersion !== 'trading_research.market_context.v1') return false;
  if (!isObject(value.instrument) || !hasString(value.instrument.code)) return false;
  if (!Array.isArray(value.referenceLevels) || !Array.isArray(value.sessions)) return false;
  if (!isObject(value.higherTimeframe)) return false;
  if (!hasString(value.higherTimeframe.trend20)) return false;
  if (!isObject(value.dayArchetype) || !Array.isArray(value.dayArchetype.reasons)) return false;
  if (!isObject(value.features) || !Array.isArray(value.intermarket)) return false;
  return true;
}

function validSetupEvent(value: unknown): boolean {
  if (!isObject(value)) return false;
  return (
    value.schemaVersion === 'trading_research.setup_event.v1' &&
    hasString(value.instrument) &&
    hasString(value.timestamp) &&
    hasString(value.eventType) &&
    isObject(value.referenceLevel) &&
    isObject(value.outcome)
  );
}

function validEventStudy(value: unknown): boolean {
  if (!isObject(value)) return false;
  return (
    value.schemaVersion === 'trading_research.event_study.v1' &&
    hasString(value.instrument) &&
    isObject(value.event) &&
    isObject(value.metrics)
  );
}

function validNullableString(value: unknown): value is string | null {
  return value === null || hasString(value);
}

function validFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function validNullableNumber(value: unknown): value is number | null {
  return value === null || validFiniteNumber(value);
}

function validNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

function validConditionalGroup(value: unknown): value is ConditionalResearchGroup {
  if (!isObject(value) || !isObject(value.dimensions) || !isObject(value.metrics)) return false;

  const dimensions = value.dimensions;
  const dimensionKeys = [
    'instrument',
    'market',
    'session',
    'dayArchetype',
    'eventType',
    'referenceLevelKind',
    'strategyId',
    'variantId',
  ];
  if (!dimensionKeys.every((key) => key in dimensions)) return false;
  if (!validNullableString(dimensions.instrument)) return false;
  if (!(dimensions.market === null || ['CN', 'HK', 'US'].includes(String(dimensions.market)))) {
    return false;
  }
  if (
    ![
      dimensions.session,
      dimensions.dayArchetype,
      dimensions.eventType,
      dimensions.referenceLevelKind,
      dimensions.strategyId,
      dimensions.variantId,
    ].every(validNullableString)
  ) {
    return false;
  }

  const metrics = value.metrics;
  if (!validNonNegativeInteger(metrics.sampleCount) || metrics.sampleCount < 1) return false;
  if (!validNonNegativeInteger(metrics.dateCount) || metrics.dateCount < 1) return false;
  if (!validNonNegativeInteger(metrics.instrumentCount) || metrics.instrumentCount < 1) return false;
  if (
    ![
      metrics.winRate,
      metrics.expectancy,
      metrics.meanReturn,
      metrics.meanMfe,
      metrics.meanMae,
    ].every(validNullableNumber)
  ) {
    return false;
  }
  const winRate = metrics.winRate;
  return winRate === null || (validFiniteNumber(winRate) && winRate >= 0 && winRate <= 1);
}

export function parseContextualResearch(value: unknown): ContextualResearchSnapshot | null {
  if (!isObject(value)) return null;
  if (value.schemaVersion !== 'trading_research.contextual_snapshot.v1') return null;
  if (!hasString(value.generatedAt) || !hasString(value.dataDate)) return null;
  if (!isObject(value.quality) || !['pass', 'warning'].includes(String(value.quality.status))) {
    return null;
  }
  if (!Array.isArray(value.quality.warnings) || !isObject(value.coverage)) return null;
  if (!Array.isArray(value.contexts) || !value.contexts.every(validContext)) return null;
  if (!Array.isArray(value.setupEvents) || !value.setupEvents.every(validSetupEvent)) return null;
  if (!Array.isArray(value.eventStudies) || !value.eventStudies.every(validEventStudy)) return null;
  return value as unknown as ContextualResearchSnapshot;
}

export function parseConditionalResearch(value: unknown): ConditionalResearchSnapshot | null {
  if (!isObject(value)) return null;
  if (value.schemaVersion !== 'trading_research.conditional_research.v1') return null;
  if (!hasString(value.generatedAt) || !isObject(value.dateRange)) return null;
  if (!hasString(value.dateRange.start) || !hasString(value.dateRange.end)) return null;
  if (!validNonNegativeInteger(value.sourceSnapshots)) return null;
  if (!isObject(value.quality) || !['pass', 'warning'].includes(String(value.quality.status))) {
    return null;
  }
  if (!Array.isArray(value.quality.warnings)) return null;
  if (!isObject(value.coverage)) return null;
  const coverage = value.coverage;
  const coverageKeys = [
    'requestedSnapshots',
    'evaluatedSnapshots',
    'skippedSnapshots',
    'setupSamples',
    'strategySamples',
  ];
  if (!coverageKeys.every((key) => validNonNegativeInteger(coverage[key]))) return null;
  if (!Array.isArray(value.groups) || !value.groups.every(validConditionalGroup)) return null;
  if (!isObject(value.provenance) || !hasString(value.provenance.source)) return null;
  if (!hasString(value.provenance.definitionVersion)) return null;
  return value as unknown as ConditionalResearchSnapshot;
}

export function selectContextualResearch(
  snapshot: ContextualResearchSnapshot | null,
  instrumentCode: string,
): SelectedContextualResearch {
  if (!snapshot) {
    return { context: null, setupEvents: [], eventStudies: [] };
  }
  return {
    context: snapshot.contexts.find((entry) => entry.instrument.code === instrumentCode) ?? null,
    setupEvents: snapshot.setupEvents
      .filter((entry) => entry.instrument === instrumentCode)
      .sort((left, right) => right.timestamp.localeCompare(left.timestamp)),
    eventStudies: snapshot.eventStudies
      .filter((entry) => entry.instrument === instrumentCode)
      .sort((left, right) => right.event.timestamp.localeCompare(left.event.timestamp)),
  };
}

export function selectConditionalResearch(
  snapshot: ConditionalResearchSnapshot | null,
  instrumentCode: string,
): ConditionalResearchGroup[] {
  if (!snapshot) return [];
  return snapshot.groups.filter((group) => group.dimensions.instrument === instrumentCode);
}
