import { snapshotFreshness } from '../researchSnapshot.ts';
import type { ResearchSnapshot } from '../types.ts';
import type {
  StrategyDetailGroup,
  StrategyRollingSummary,
  StrategySnapshot,
  StrategyVariant,
} from './strategySnapshot';

function text(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? '—' : String(value);
}

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null): string {
  return value === null ? '—' : value.toLocaleString('zh-CN');
}

function normalizeVariant(variant: ResearchSnapshot['variants'][number]): StrategyVariant {
  return { ...variant };
}

function normalizeSummary(
  summary: ResearchSnapshot['walkForward']['summaries'][number],
): StrategyRollingSummary {
  return { ...summary };
}

function detailGroups(snapshot: ResearchSnapshot): StrategyDetailGroup[] {
  const warmup = snapshot.coverage.contextWarmup;
  const checks = snapshot.quality.checks;
  const manifest = snapshot.source.dataPlatformManifest;

  return [
    {
      id: 'coverage',
      label: '数据覆盖',
      items: [
        { label: '行业映射置信度', value: snapshot.mapping.confidence },
        { label: '映射行业数', value: formatNumber(snapshot.mapping.mappedIndustryCodes) },
        { label: '行业代理数', value: formatNumber(snapshot.mapping.mappedProxyIndustryCodes) },
        { label: '股票覆盖率', value: formatPercent(snapshot.mapping.coverage.symbolCoverage) },
        { label: '上下文预热规则', value: text(warmup.rule) },
        { label: '上下文预热跳过', value: formatNumber(warmup.skippedSymbols) },
      ],
    },
    {
      id: 'quality',
      label: '质量检查',
      items: [
        { label: '覆盖数量对账', value: checks.coverageCountsReconcile ? '通过' : '警告' },
        { label: '策略变体完整', value: checks.expectedVariantsPresent ? '通过' : '警告' },
        { label: 'fold key 唯一', value: checks.foldKeysUnique ? '通过' : '警告' },
        { label: 'OOS 记录非空', value: checks.oosRowsPresent ? '通过' : '警告' },
        {
          label: '来源追踪',
          value: checks.provenanceComplete === undefined
            ? '历史 v1 未提供'
            : checks.provenanceComplete
              ? '通过'
              : '警告',
        },
      ],
    },
    {
      id: 'execution',
      label: '执行约束',
      items: [{ label: '执行时点', value: text(snapshot.executionConstraints.timing) }],
    },
    {
      id: 'provenance',
      label: '研究来源',
      items: [
        { label: '快照契约', value: snapshot.schemaVersion },
        { label: '研究 commit', value: text(snapshot.source.researchCommit) },
        { label: 'OOS 日期', value: text(snapshot.source.oosGeneratedAt) },
        { label: '数据平台', value: snapshot.source.dataPlatform },
        { label: '数据 manifest', value: text(manifest?.schemaVersion) },
        { label: 'manifest 生成', value: text(manifest?.generatedAt) },
      ],
    },
  ];
}

export function adaptNiuMenSnapshot(
  snapshot: ResearchSnapshot,
  dashboardDate: string,
): StrategySnapshot {
  return {
    strategyId: 'niu-men-line',
    strategyLabel: '牛门线',
    schemaVersion: snapshot.schemaVersion,
    generatedAt: snapshot.generatedAt,
    dataDate: snapshot.source.dataDate,
    freshness: snapshotFreshness(dashboardDate, snapshot),
    quality: snapshot.quality.status,
    coverage: {
      requested: snapshot.coverage.requestedSymbols,
      evaluated: snapshot.coverage.evaluatedSymbols,
      skipped: snapshot.coverage.skippedSymbols,
    },
    variants: snapshot.variants.map(normalizeVariant),
    rollingSummaries: snapshot.walkForward.summaries.map(normalizeSummary),
    walkForward: {
      trainBars: snapshot.walkForward.trainBars,
      testBars: snapshot.walkForward.testBars,
      stepBars: snapshot.walkForward.stepBars,
      semantics: snapshot.walkForward.foldSemantics,
    },
    executionTiming: snapshot.executionConstraints.timing,
    provenance: {
      researchCommit: snapshot.source.researchCommit ?? null,
      dataPlatform: snapshot.source.dataPlatform,
      dataPlatformSchemaVersion: snapshot.source.dataPlatformManifest?.schemaVersion ?? null,
      dataPlatformGeneratedAt: snapshot.source.dataPlatformManifest?.generatedAt ?? null,
      oosSchemaVersion: snapshot.source.oosSchemaVersion,
      oosGeneratedAt: snapshot.source.oosGeneratedAt ?? null,
    },
    details: detailGroups(snapshot),
  };
}
