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
