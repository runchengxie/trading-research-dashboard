import type { ResearchSnapshot } from './types';

export type ResearchFreshness = 'current' | 'stale' | 'unknown';

type JsonRecord = Record<string, unknown>;

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const V1 = 'niu_men.research_snapshot.v1';
const V2 = 'niu_men.research_snapshot.v2';

function asRecord(value: unknown, label: string): JsonRecord {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`研究快照结构错误：${label} 必须是对象`);
  }
  return value as JsonRecord;
}

function asString(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`研究快照结构错误：${label} 必须是非空字符串`);
  }
  return value;
}

function asNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`研究快照结构错误：${label} 必须是有限数字`);
  }
  return value;
}

function asNullableNumber(value: unknown, label: string): number | null {
  if (value === null) return null;
  return asNumber(value, label);
}

function asBoolean(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') {
    throw new Error(`研究快照结构错误：${label} 必须是布尔值`);
  }
  return value;
}

function asNullableString(value: unknown, label: string): string | null {
  if (value === null) return null;
  return asString(value, label);
}

function validateAssets(value: unknown): void {
  const assets = asRecord(value, 'source.assets');
  for (const key of [
    'stockPool',
    'industryChanges',
    'industryAudit',
    'industryContext',
    'dailyCleanRoot',
    'folds',
    'summary',
    'skips',
  ]) {
    if (!(key in assets)) {
      throw new Error(`研究快照结构错误：source.assets.${key} 缺失`);
    }
    asNullableString(assets[key], `source.assets.${key}`);
  }
}

function validateVariant(value: unknown, index: number): void {
  const variant = asRecord(value, `variants[${index}]`);
  asString(variant.id, `variants[${index}].id`);
  asString(variant.label, `variants[${index}].label`);
  asNumber(variant.symbols, `variants[${index}].symbols`);
  asNumber(variant.foldRows, `variants[${index}].foldRows`);
  for (const key of [
    'annualizedReturnMedian',
    'sharpeMedian',
    'maxDrawdownMedian',
    'tradeCountMedian',
    'winRateMedian',
    'profitFactorMedian',
    'entrySignalCount',
    'blockedEntryCount',
    'blockedExitDayCount',
    'sectorRetreatBlockCount',
    'priceRegimeBlockCount',
  ]) {
    asNullableNumber(variant[key], `variants[${index}].${key}`);
  }
}

function validateRollingSummary(value: unknown, index: number): void {
  const summary = asRecord(value, `walkForward.summaries[${index}]`);
  asString(summary.variant, `walkForward.summaries[${index}].variant`);
  asNumber(summary.foldId, `walkForward.summaries[${index}].foldId`);
  asNumber(summary.symbols, `walkForward.summaries[${index}].symbols`);
  for (const key of [
    'annualizedReturnMedian',
    'sharpeMedian',
    'maxDrawdownMedian',
    'tradeCountMedian',
    'winRateMedian',
    'profitFactorMedian',
    'entrySignalCount',
    'sectorRetreatBlockCount',
    'priceRegimeBlockCount',
  ]) {
    asNullableNumber(summary[key], `walkForward.summaries[${index}].${key}`);
  }
}

export function researchFreshness(
  dashboardDate: string,
  researchDate: string,
): ResearchFreshness {
  if (!DATE_RE.test(dashboardDate) || !DATE_RE.test(researchDate)) {
    return 'unknown';
  }
  return researchDate < dashboardDate ? 'stale' : 'current';
}

export function parseResearchSnapshot(value: unknown): ResearchSnapshot {
  const root = asRecord(value, 'root');
  const schemaVersion = asString(root.schemaVersion, 'schemaVersion');
  if (schemaVersion !== V1 && schemaVersion !== V2) {
    throw new Error(`不支持的研究快照版本：${schemaVersion}`);
  }
  asString(root.generatedAt, 'generatedAt');

  const source = asRecord(root.source, 'source');
  if (asString(source.researchEngine, 'source.researchEngine') !== 'niu-men-line-strategy') {
    throw new Error('研究快照结构错误：source.researchEngine 不受支持');
  }
  asString(source.dataPlatform, 'source.dataPlatform');
  asString(source.dataDate, 'source.dataDate');
  asString(source.oosSchemaVersion, 'source.oosSchemaVersion');
  validateAssets(source.assets);

  if (schemaVersion === V2) {
    if (
      !('researchCommit' in source) ||
      !('oosGeneratedAt' in source) ||
      !('dataPlatformManifest' in source)
    ) {
      throw new Error('研究快照 v2 来源信息不完整');
    }
    asNullableString(source.researchCommit, 'source.researchCommit');
    asString(source.oosGeneratedAt, 'source.oosGeneratedAt');
    const manifest = asRecord(source.dataPlatformManifest, 'source.dataPlatformManifest');
    if (!('schemaVersion' in manifest) || !('generatedAt' in manifest)) {
      throw new Error('研究快照 v2 来源信息不完整');
    }
    asNullableString(manifest.schemaVersion, 'source.dataPlatformManifest.schemaVersion');
    asNullableString(manifest.generatedAt, 'source.dataPlatformManifest.generatedAt');
  }

  const mapping = asRecord(root.mapping, 'mapping');
  const confidence = asString(mapping.confidence, 'mapping.confidence');
  if (confidence !== 'expanded' && confidence !== 'high') {
    throw new Error(`研究快照结构错误：mapping.confidence=${confidence}`);
  }
  asNumber(mapping.mappedIndustryCodes, 'mapping.mappedIndustryCodes');
  asNumber(mapping.mappedProxyIndustryCodes, 'mapping.mappedProxyIndustryCodes');
  const mappingCoverage = asRecord(mapping.coverage, 'mapping.coverage');
  asNullableNumber(mappingCoverage.industryRowCoverage, 'mapping.coverage.industryRowCoverage');
  asNullableNumber(mappingCoverage.symbolCoverage, 'mapping.coverage.symbolCoverage');

  const coverage = asRecord(root.coverage, 'coverage');
  asNumber(coverage.requestedSymbols, 'coverage.requestedSymbols');
  asNumber(coverage.evaluatedSymbols, 'coverage.evaluatedSymbols');
  asNumber(coverage.skippedSymbols, 'coverage.skippedSymbols');
  asRecord(coverage.skipReasons, 'coverage.skipReasons');
  const warmup = asRecord(coverage.contextWarmup, 'coverage.contextWarmup');
  asString(warmup.rule, 'coverage.contextWarmup.rule');
  asNumber(warmup.minBars, 'coverage.contextWarmup.minBars');
  asNumber(warmup.skippedSymbols, 'coverage.contextWarmup.skippedSymbols');
  asNullableNumber(warmup.contextRows, 'coverage.contextWarmup.contextRows');
  asNullableNumber(warmup.readyRows, 'coverage.contextWarmup.readyRows');
  asNullableNumber(warmup.warmupRows, 'coverage.contextWarmup.warmupRows');

  const walkForward = asRecord(root.walkForward, 'walkForward');
  asNumber(walkForward.trainBars, 'walkForward.trainBars');
  asNumber(walkForward.testBars, 'walkForward.testBars');
  asNumber(walkForward.stepBars, 'walkForward.stepBars');
  asString(walkForward.foldSemantics, 'walkForward.foldSemantics');
  if (!Array.isArray(walkForward.summaries)) {
    throw new Error('研究快照结构错误：walkForward.summaries 必须是数组');
  }
  walkForward.summaries.forEach(validateRollingSummary);

  if (!Array.isArray(root.variants)) {
    throw new Error('研究快照结构错误：variants 必须是数组');
  }
  root.variants.forEach(validateVariant);

  const execution = asRecord(root.executionConstraints, 'executionConstraints');
  asString(execution.timing, 'executionConstraints.timing');
  asRecord(execution.byVariant, 'executionConstraints.byVariant');

  const quality = asRecord(root.quality, 'quality');
  const status = asString(quality.status, 'quality.status');
  if (status !== 'pass' && status !== 'warning') {
    throw new Error(`研究快照结构错误：quality.status=${status}`);
  }
  const checks = asRecord(quality.checks, 'quality.checks');
  asBoolean(checks.coverageCountsReconcile, 'quality.checks.coverageCountsReconcile');
  asBoolean(checks.expectedVariantsPresent, 'quality.checks.expectedVariantsPresent');
  asBoolean(checks.foldKeysUnique, 'quality.checks.foldKeysUnique');
  asBoolean(checks.oosRowsPresent, 'quality.checks.oosRowsPresent');
  if (schemaVersion === V2) {
    if (!('provenanceComplete' in checks)) {
      throw new Error('研究快照 v2 来源信息不完整');
    }
    asBoolean(checks.provenanceComplete, 'quality.checks.provenanceComplete');
  }
  asNullableNumber(quality.duplicateFoldRows, 'quality.duplicateFoldRows');

  return root as unknown as ResearchSnapshot;
}
