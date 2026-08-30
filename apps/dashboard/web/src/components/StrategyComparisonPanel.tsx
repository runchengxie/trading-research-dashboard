import type { StrategyLoadResult } from '../api.ts';
import type { StrategySnapshot } from '../research/strategySnapshot.ts';
import { formatComparisonMetric } from '../research/comparisonLabels.ts';
import { defaultVariantFor } from '../research/defaultVariants.ts';
import { formatExecutionConstraint } from '../research/executionLabels.ts';
import '../research.css';

function publishedSnapshots(results: StrategyLoadResult[]): StrategySnapshot[] {
  return results.flatMap((result) => (result.snapshot ? [result.snapshot] : []));
}

export default function StrategyComparisonPanel({
  results,
}: {
  results: StrategyLoadResult[];
}) {
  const snapshots = publishedSnapshots(results);

  return (
    <section className="research-section" aria-labelledby="strategy-comparison-title">
      <div className="research-section-head">
        <div>
          <p className="research-kicker">策略研究</p>
          <h2 id="strategy-comparison-title">策略对比</h2>
          <p className="research-subtitle">只比较已经通过快照契约并成功发布的策略。</p>
        </div>
      </div>

      {snapshots.length < 2 ? (
        <div className="research-empty strategy-comparison-empty">
          <strong>需要第二个已发布快照</strong>
          <p>
            当前只有 {snapshots.length} 个策略快照可用。R-Breaker 研究发布后，
            这里会自动出现共同变体指标对比。
          </p>
        </div>
      ) : (
        <div className="research-card">
          <DefaultStrategyOverview snapshots={snapshots} />
          <div className="research-card-head">
            <div>
              <h3>共同变体指标</h3>
              <p>策略快照按 variant id 对齐；未提供指标和无共同变体分别标注。</p>
            </div>
          </div>
          <ComparisonTable snapshots={snapshots} />
        </div>
      )}
    </section>
  );
}

function DefaultStrategyOverview({ snapshots }: { snapshots: StrategySnapshot[] }) {
  const defaults = snapshots.flatMap((snapshot) => {
    const variant = defaultVariantFor(snapshot);
    return variant ? [{ snapshot, variant }] : [];
  });

  return (
    <div className="strategy-default-overview">
      <div className="research-card-head">
        <div>
          <h3>策略默认版本概览</h3>
          <p>各策略按自身约定的默认 variant 并列展示，仅作方向性观察，不代表同条件横向回测。</p>
        </div>
      </div>
      <div className="research-table-wrap">
        <table className="research-table strategy-default-table">
          <thead>
            <tr>
              <th>策略</th>
              <th>默认变体</th>
              <th>年化</th>
              <th>Sharpe</th>
              <th>回撤</th>
              <th>交易次数</th>
              <th>覆盖标的</th>
              <th>涨停阻止买入</th>
              <th>跌停阻止卖出日</th>
            </tr>
          </thead>
          <tbody>
            {defaults.map(({ snapshot, variant }) => (
              <tr key={`${snapshot.strategyId}-${variant.id}`}>
                <td>{snapshot.strategyLabel}</td>
                <td><code>{variant.id}</code></td>
                <td>{formatComparisonMetric(variant.annualizedReturnMedian, variant.annualizedReturnMedian === null ? 'not_provided' : 'value', 'percent')}</td>
                <td>{formatComparisonMetric(variant.sharpeMedian, variant.sharpeMedian === null ? 'not_provided' : 'value', 'number')}</td>
                <td>{formatComparisonMetric(variant.maxDrawdownMedian, variant.maxDrawdownMedian === null ? 'not_provided' : 'value', 'percent')}</td>
                <td>{variant.tradeCountMedian === null ? '未提供' : variant.tradeCountMedian.toFixed(1)}</td>
                <td>{variant.symbols.toLocaleString('zh-CN')}</td>
                <td>{formatExecutionConstraint(variant.blockedEntryCount, variant.executionCapabilities?.blockedEntry ?? 'not_modelled')}</td>
                <td>{formatExecutionConstraint(variant.blockedExitDayCount, variant.executionCapabilities?.blockedExitDay ?? 'not_modelled')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ComparisonTable({ snapshots }: { snapshots: StrategySnapshot[] }) {
  return (
    <div className="research-table-wrap">
      <table className="research-table strategy-comparison-table">
        <thead>
          <tr>
            <th>策略变体</th>
            {snapshots.map((snapshot) => (
              <th key={snapshot.strategyId} colSpan={3}>
                {snapshot.strategyLabel}
              </th>
            ))}
          </tr>
          <tr>
            <th />
            {snapshots.flatMap((snapshot) => [
              <th key={`${snapshot.strategyId}-return`}>年化</th>,
              <th key={`${snapshot.strategyId}-sharpe`}>Sharpe</th>,
              <th key={`${snapshot.strategyId}-drawdown`}>回撤</th>,
            ])}
          </tr>
        </thead>
        <tbody>
          {snapshots.flatMap((snapshot) => snapshot.variants.map((variant) => (
            <tr key={`${snapshot.strategyId}-${variant.id}`}>
              <td><span>{snapshot.strategyLabel}</span><br /><code>{variant.id}</code></td>
              {snapshots.flatMap((column) => {
                if (column.strategyId !== snapshot.strategyId) {
                  return [
                    <td key={`${column.strategyId}-${variant.id}-return`}>{formatComparisonMetric(null, 'not_shared', 'percent')}</td>,
                    <td key={`${column.strategyId}-${variant.id}-sharpe`}>{formatComparisonMetric(null, 'not_shared', 'number')}</td>,
                    <td key={`${column.strategyId}-${variant.id}-drawdown`}>{formatComparisonMetric(null, 'not_shared', 'percent')}</td>,
                  ];
                }
                return [
                  <td key={`${snapshot.strategyId}-${variant.id}-return`}>{formatComparisonMetric(variant.annualizedReturnMedian, variant.annualizedReturnMedian === null ? 'not_provided' : 'value', 'percent')}</td>,
                  <td key={`${snapshot.strategyId}-${variant.id}-sharpe`}>{formatComparisonMetric(variant.sharpeMedian, variant.sharpeMedian === null ? 'not_provided' : 'value', 'number')}</td>,
                  <td key={`${snapshot.strategyId}-${variant.id}-drawdown`}>{formatComparisonMetric(variant.maxDrawdownMedian, variant.maxDrawdownMedian === null ? 'not_provided' : 'value', 'percent')}</td>,
                ];
              })}
            </tr>
          ))) }
        </tbody>
      </table>
    </div>
  );
}
