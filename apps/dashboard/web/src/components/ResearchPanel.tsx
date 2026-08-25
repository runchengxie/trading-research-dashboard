import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react/esm/core';
import type { StrategySnapshot, StrategyVariant } from '../research/strategySnapshot.ts';
import { paletteFor, type ThemeMode } from '../theme';
import { echarts } from '../echarts';
import '../research.css';

interface ResearchPanelProps {
  snapshot: StrategySnapshot;
  theme: ThemeMode;
}

function formatPercent(value: number | null, digits = 2): string {
  return value === null || Number.isNaN(value) ? '—' : `${(value * 100).toFixed(digits)}%`;
}

function formatNumber(value: number | null, digits = 2): string {
  return value === null || Number.isNaN(value) ? '—' : value.toFixed(digits);
}

function formatCount(value: number | null): string {
  return value === null || Number.isNaN(value)
    ? '—'
    : Math.round(value).toLocaleString('zh-CN');
}

function qualityLabel(snapshot: StrategySnapshot): string {
  return snapshot.quality === 'pass' ? '数据质量检查通过' : '数据质量存在警告';
}

function freshnessLabel(snapshot: StrategySnapshot): string {
  if (snapshot.freshness === 'current') return '研究数据与行情同步';
  if (snapshot.freshness === 'stale') return '研究快照已过期';
  return '研究新鲜度未知';
}

function VariantTable({ variants }: { variants: StrategyVariant[] }) {
  return (
    <div className="research-table-wrap">
      <table className="research-table">
        <thead>
          <tr>
            <th>策略变体</th>
            <th>年化收益中位数</th>
            <th>Sharpe 中位数</th>
            <th>最大回撤中位数</th>
            <th>交易次数中位数</th>
            <th>覆盖标的</th>
            <th>涨停阻止买入</th>
            <th>跌停阻止卖出日</th>
          </tr>
        </thead>
        <tbody>
          {variants.map((variant) => (
            <tr key={variant.id}>
              <td>
                <span className="research-variant-label">{variant.label}</span>
                <code>{variant.id}</code>
              </td>
              <td>{formatPercent(variant.annualizedReturnMedian)}</td>
              <td>{formatNumber(variant.sharpeMedian, 3)}</td>
              <td>{formatPercent(variant.maxDrawdownMedian)}</td>
              <td>{formatNumber(variant.tradeCountMedian, 1)}</td>
              <td>{variant.symbols.toLocaleString('zh-CN')}</td>
              <td>{formatCount(variant.blockedEntryCount)}</td>
              <td>{formatCount(variant.blockedExitDayCount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RollingReturnChart({
  snapshot,
  theme,
}: {
  snapshot: StrategySnapshot;
  theme: ThemeMode;
}) {
  const option = useMemo(() => {
    const palette = paletteFor(theme);
    const foldIds = Array.from(
      new Set(snapshot.rollingSummaries.map((item) => item.foldId)),
    ).sort((a, b) => a - b);
    const byVariant = new Map<string, Map<number, number | null>>();

    for (const item of snapshot.rollingSummaries) {
      const foldMap = byVariant.get(item.variant) ?? new Map<number, number | null>();
      foldMap.set(item.foldId, item.annualizedReturnMedian);
      byVariant.set(item.variant, foldMap);
    }

    return {
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value: unknown) =>
          typeof value === 'number' ? `${value.toFixed(2)}%` : '—',
      },
      legend: {
        type: 'scroll',
        top: 0,
        textStyle: { color: palette.axisLabelColor },
      },
      grid: { left: 58, right: 20, top: 52, bottom: 42 },
      xAxis: {
        type: 'category',
        data: foldIds.map((foldId) => `窗口 ${foldId + 1}`),
        axisLine: { lineStyle: { color: palette.axisLineColor } },
        axisLabel: { color: palette.axisLabelColor },
      },
      yAxis: {
        type: 'value',
        name: '年化收益中位数',
        nameTextStyle: { color: palette.axisLabelColor },
        axisLine: { lineStyle: { color: palette.axisLineColor } },
        axisLabel: {
          color: palette.axisLabelColor,
          formatter: (value: number) => `${value.toFixed(1)}%`,
        },
        splitLine: {
          lineStyle: {
            color: palette.axisLineColor,
            opacity: theme === 'dark' ? 0.28 : 0.18,
          },
        },
      },
      series: snapshot.variants.map((variant) => {
        const foldMap = byVariant.get(variant.id) ?? new Map<number, number | null>();
        return {
          name: variant.label,
          type: 'line',
          smooth: false,
          connectNulls: false,
          symbolSize: 5,
          data: foldIds.map((foldId) => {
            const value = foldMap.get(foldId);
            return value === null || value === undefined ? null : value * 100;
          }),
        };
      }),
    };
  }, [snapshot, theme]);

  if (snapshot.rollingSummaries.length === 0) {
    return <div className="research-empty">当前快照没有滚动窗口摘要。</div>;
  }

  return (
    <ReactECharts
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ width: '100%', height: 360 }}
    />
  );
}

function DetailGroups({ snapshot }: { snapshot: StrategySnapshot }) {
  return (
    <div className="research-detail-grid">
      {snapshot.details.map((group) => (
        <div key={group.id}>
          <h4>{group.label}</h4>
          <dl className="research-detail-list">
            {group.items.map((item) => (
              <div key={`${group.id}-${item.label}`}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}

export default function ResearchPanel({ snapshot, theme }: ResearchPanelProps) {
  return (
    <section className="research-section" aria-labelledby="research-title">
      <div className="research-section-head">
        <div>
          <p className="research-kicker">策略研究</p>
          <h2 id="research-title">{snapshot.strategyLabel}全市场样本外研究</h2>
          <p className="research-subtitle">
            数据截止 {snapshot.dataDate} · 快照 {snapshot.generatedAt}
          </p>
        </div>
        <div className="research-status-group">
          <span className={`research-freshness research-freshness-${snapshot.freshness}`}>
            {freshnessLabel(snapshot)}
          </span>
          <span className={`research-quality research-quality-${snapshot.quality}`}>
            {qualityLabel(snapshot)}
          </span>
        </div>
      </div>

      {snapshot.freshness === 'stale' && (
        <div className="research-stale-warning" role="status">
          当前行情数据日期晚于研究数据截止日。下方研究结果不是当前行情日期重新计算的结果。
        </div>
      )}

      {snapshot.freshness === 'unknown' && (
        <div className="research-stale-warning" role="status">
          当前研究快照缺少足够的来源时间信息，暂不判断新鲜度。
        </div>
      )}

      <div className="research-kpi-grid">
        <div className="research-kpi">
          <span>评估覆盖</span>
          <strong>
            {snapshot.coverage.evaluated.toLocaleString('zh-CN')} /{' '}
            {snapshot.coverage.requested.toLocaleString('zh-CN')}
          </strong>
          <small>跳过 {snapshot.coverage.skipped.toLocaleString('zh-CN')} 只</small>
        </div>
        <div className="research-kpi">
          <span>策略变体</span>
          <strong>{snapshot.variants.length}</strong>
          <small>{snapshot.strategyLabel} 发布快照</small>
        </div>
        <div className="research-kpi">
          <span>滚动 OOS</span>
          <strong>
            {snapshot.walkForward.trainBars}/{snapshot.walkForward.testBars}/
            {snapshot.walkForward.stepBars}
          </strong>
          <small>训练 / 测试 / 步长 bar</small>
        </div>
        <div className="research-kpi">
          <span>研究来源</span>
          <strong>{snapshot.provenance.researchCommit ? '可追踪' : '历史快照'}</strong>
          <small>{snapshot.provenance.dataPlatform}</small>
        </div>
      </div>

      <div className="research-card">
        <div className="research-card-head">
          <div>
            <h3>策略变体 OOS 指标</h3>
            <p>指标按所有股票与样本外窗口记录汇总，展示中位数与成交约束计数。</p>
          </div>
        </div>
        <VariantTable variants={snapshot.variants} />
      </div>

      <div className="research-card">
        <div className="research-card-head">
          <div>
            <h3>滚动窗口年化收益中位数</h3>
            <p>{snapshot.walkForward.semantics}</p>
          </div>
        </div>
        <RollingReturnChart snapshot={snapshot} theme={theme} />
      </div>

      <details className="research-details">
        <summary>覆盖、质量、来源与成交约束详情</summary>
        <DetailGroups snapshot={snapshot} />
      </details>
    </section>
  );
}

