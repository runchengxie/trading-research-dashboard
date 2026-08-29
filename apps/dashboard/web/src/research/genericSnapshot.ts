import { researchFreshness } from '../researchSnapshot.ts';
import type {
  StrategyDetailGroup,
  StrategyRollingSummary,
  StrategySnapshot,
  StrategyVariant,
} from './strategySnapshot.ts';

export const GENERIC_SNAPSHOT_VERSION = 'trading_research.strategy_snapshot.v1';

export interface GenericStrategyIdentity {
  id: string;
  label: string;
  description?: string;
}

export interface GenericProvenance {
  researchCommit: string | null;
  dataPlatform?: string;
  dataPlatformSchemaVersion: string | null;
  dataPlatformGeneratedAt: string | null;
  oosSchemaVersion: string;
  oosGeneratedAt: string | null;
}

export interface GenericVariant {
  id: string;
  label: string;
  symbols?: number;
  foldRows?: number;
  metrics: Record<string, number | null>;
}

export interface GenericEnvelope {
  schemaVersion: string;
  strategy: GenericStrategyIdentity;
  generatedAt: string;
  dataDate: string;
  quality: { status: 'pass' | 'warning'; checks?: Record<string, boolean> };
  provenance: GenericProvenance;
  coverage: { requested: number; evaluated: number; skipped: number };
  walkForward: {
    trainBars: number;
    testBars: number;
    stepBars: number;
    semantics: string;
    summaries: Array<{
      variant: string;
      foldId: number;
      symbols: number;
      metrics: Record<string, number | null>;
      startDate?: string;
      endDate?: string;
    }>;
  } | null;
  executionTiming: string | null;
  variants: GenericVariant[];
  details?: StrategyDetailGroup[];
  source?: { wireVersion: string; payload: unknown };
}

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown, label: string): JsonRecord {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`通用策略快照结构错误：${label} 必须是对象`);
  }
  return value as JsonRecord;
}

function asString(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`通用策略快照结构错误：${label} 必须是非空字符串`);
  }
  return value;
}

function asNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`通用策略快照结构错误：${label} 必须是有限数字`);
  }
  return value;
}

function asMetricsMap(value: unknown, label: string): Record<string, number | null> {
  const record = asRecord(value, label);
  const metrics: Record<string, number | null> = {};
  for (const [key, entry] of Object.entries(record)) {
    if (entry !== null && typeof entry !== 'number') {
      throw new Error(`通用策略快照结构错误：${label}.${key} 必须是数字或 null`);
    }
    metrics[key] = entry;
  }
  return metrics;
}

function asOptionalDate(value: unknown, label: string): string | undefined {
  if (value === undefined) return undefined;
  return asString(value, label);
}

export function parseStrategyEnvelope(value: unknown): GenericEnvelope {
  const root = asRecord(value, 'root');
  const schemaVersion = asString(root.schemaVersion, 'schemaVersion');
  if (schemaVersion !== GENERIC_SNAPSHOT_VERSION) {
    throw new Error(`不支持的通用策略快照版本：${schemaVersion}`);
  }

  const strategy = asRecord(root.strategy, 'strategy');
  asString(strategy.id, 'strategy.id');
  asString(strategy.label, 'strategy.label');
  const quality = asRecord(root.quality, 'quality');
  const status = asString(quality.status, 'quality.status');
  if (status !== 'pass' && status !== 'warning') {
    throw new Error(`通用策略快照结构错误：quality.status=${status}`);
  }
  const provenance = asRecord(root.provenance, 'provenance');
  asString(provenance.oosSchemaVersion, 'provenance.oosSchemaVersion');
  asString(root.dataDate, 'dataDate');
  asString(root.generatedAt, 'generatedAt');

  const coverage = asRecord(root.coverage, 'coverage');
  asNumber(coverage.requested, 'coverage.requested');
  asNumber(coverage.evaluated, 'coverage.evaluated');
  asNumber(coverage.skipped, 'coverage.skipped');

  if (!Array.isArray(root.variants) || root.variants.length === 0) {
    throw new Error('通用策略快照结构错误：variants 必须是非空数组');
  }
  root.variants.forEach((variant, index) => {
    const record = asRecord(variant, `variants[${index}]`);
    asString(record.id, `variants[${index}].id`);
    asString(record.label, `variants[${index}].label`);
    asMetricsMap(record.metrics, `variants[${index}].metrics`);
  });

  const walkForward = root.walkForward === undefined || root.walkForward === null
    ? null
    : asRecord(root.walkForward, 'walkForward');
  if (walkForward !== null) {
    if (!Array.isArray(walkForward.summaries)) {
      throw new Error('通用策略快照结构错误：walkForward.summaries 必须是数组');
    }
    walkForward.summaries.forEach((summary, index) => {
      const record = asRecord(summary, `walkForward.summaries[${index}]`);
      asOptionalDate(record.startDate, `walkForward.summaries[${index}].startDate`);
      asOptionalDate(record.endDate, `walkForward.summaries[${index}].endDate`);
    });
  }

  const source = root.source === undefined ? undefined : asRecord(root.source, 'source');
  if (source !== undefined) {
    asString(source.wireVersion, 'source.wireVersion');
    asRecord(source.payload, 'source.payload');
  }

  return root as unknown as GenericEnvelope;
}

const SUMMARY_METRIC_KEYS = [
  'annualizedReturnMedian',
  'sharpeMedian',
  'maxDrawdownMedian',
  'tradeCountMedian',
  'winRateMedian',
  'profitFactorMedian',
  'entrySignalCount',
  'sectorRetreatBlockCount',
  'priceRegimeBlockCount',
] as const;

function toVariant(variant: GenericVariant): StrategyVariant {
  return {
    id: variant.id,
    label: variant.label,
    symbols: variant.symbols ?? 0,
    foldRows: variant.foldRows ?? 0,
    annualizedReturnMedian: variant.metrics.annualizedReturnMedian ?? null,
    sharpeMedian: variant.metrics.sharpeMedian ?? null,
    maxDrawdownMedian: variant.metrics.maxDrawdownMedian ?? null,
    tradeCountMedian: variant.metrics.tradeCountMedian ?? null,
    winRateMedian: variant.metrics.winRateMedian ?? null,
    profitFactorMedian: variant.metrics.profitFactorMedian ?? null,
    entrySignalCount: variant.metrics.entrySignalCount ?? null,
    blockedEntryCount: variant.metrics.blockedEntryCount ?? null,
    blockedExitDayCount: variant.metrics.blockedExitDayCount ?? null,
    sectorRetreatBlockCount: variant.metrics.sectorRetreatBlockCount ?? null,
    priceRegimeBlockCount: variant.metrics.priceRegimeBlockCount ?? null,
  };
}

function toSummaries(envelope: GenericEnvelope): StrategyRollingSummary[] {
  const walkForward = envelope.walkForward;
  if (!walkForward) return [];
  return walkForward.summaries.map((summary) => ({
    variant: summary.variant,
    foldId: summary.foldId,
    symbols: summary.symbols,
    ...(summary.startDate ? { startDate: summary.startDate } : {}),
    ...(summary.endDate ? { endDate: summary.endDate } : {}),
    ...Object.fromEntries(
      SUMMARY_METRIC_KEYS.map((key) => [key, summary.metrics[key] ?? null]),
    ),
  })) as StrategyRollingSummary[];
}

export function envelopeToStrategySnapshot(
  envelope: GenericEnvelope,
  dashboardDate: string,
): StrategySnapshot {
  const checks = envelope.quality.checks ?? {};
  const freshness =
    checks.provenanceComplete === false
      ? 'unknown'
      : researchFreshness(dashboardDate, envelope.dataDate);

  return {
    strategyId: envelope.strategy.id,
    strategyLabel: envelope.strategy.label,
    schemaVersion: envelope.source?.wireVersion ?? envelope.schemaVersion,
    generatedAt: envelope.generatedAt,
    dataDate: envelope.dataDate,
    freshness,
    quality: envelope.quality.status,
    coverage: envelope.coverage,
    variants: envelope.variants.map(toVariant),
    rollingSummaries: toSummaries(envelope),
    walkForward: envelope.walkForward
      ? {
          trainBars: envelope.walkForward.trainBars,
          testBars: envelope.walkForward.testBars,
          stepBars: envelope.walkForward.stepBars,
          semantics: envelope.walkForward.semantics,
        }
      : { trainBars: 0, testBars: 0, stepBars: 0, semantics: '—' },
    executionTiming: envelope.executionTiming ?? '—',
    provenance: {
      researchCommit: envelope.provenance.researchCommit ?? null,
      dataPlatform: envelope.provenance.dataPlatform ?? '',
      dataPlatformSchemaVersion: envelope.provenance.dataPlatformSchemaVersion ?? null,
      dataPlatformGeneratedAt: envelope.provenance.dataPlatformGeneratedAt ?? null,
      oosSchemaVersion: envelope.provenance.oosSchemaVersion,
      oosGeneratedAt: envelope.provenance.oosGeneratedAt ?? null,
    },
    details: envelope.details ?? [],
  };
}
