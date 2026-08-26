import type { StrategyLoadResult } from '../api.ts';
import type { StrategySnapshot } from '../research/strategySnapshot.ts';
import '../research.css';

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null, digits = 3): string {
  return value === null ? '—' : value.toFixed(digits);
}

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
          <div className="research-card-head">
            <div>
              <h3>共同变体指标</h3>
              <p>策略快照按 variant id 对齐，缺失指标显示为破折号。</p>
            </div>
          </div>
          <ComparisonTable snapshots={snapshots} />
        </div>
      )}
    </section>
  );
}

function ComparisonTable({ snapshots }: { snapshots: StrategySnapshot[] }) {
  const variants = Array.from(
    new Set(snapshots.flatMap((snapshot) => snapshot.variants.map((variant) => variant.id))),
  );

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
          {variants.map((variantId) => (
            <tr key={variantId}>
              <td><code>{variantId}</code></td>
              {snapshots.flatMap((snapshot) => {
                const variant = snapshot.variants.find((item) => item.id === variantId);
                return [
                  <td key={`${snapshot.strategyId}-${variantId}-return`}>
                    {formatPercent(variant?.annualizedReturnMedian ?? null)}
                  </td>,
                  <td key={`${snapshot.strategyId}-${variantId}-sharpe`}>
                    {formatNumber(variant?.sharpeMedian ?? null)}
                  </td>,
                  <td key={`${snapshot.strategyId}-${variantId}-drawdown`}>
                    {formatPercent(variant?.maxDrawdownMedian ?? null)}
                  </td>,
                ];
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

