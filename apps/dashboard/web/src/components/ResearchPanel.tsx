import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react/esm/core';
import type { ResearchSnapshot, ResearchVariant } from '../types';
import { paletteFor, type ThemeMode } from '../theme';
import { echarts } from '../echarts';
import '../research.css';

interface ResearchPanelProps {
  snapshot: ResearchSnapshot | null;
  loaded: boolean;
  error: string | null;
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

function qualityLabel(snapshot: ResearchSnapshot): string {
  return snapshot.quality.status === 'pass' ? '数据质量检查通过' : '数据质量存在警告';
}

function VariantTable({ variants }: { variants: ResearchVariant[] }) {
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
  snapshot: ResearchSnapshot;
  theme: ThemeMode;
}) {
  const option = useMemo(() => {
    const palette = paletteFor(theme);
    const foldIds = Array.from(
      new Set(snapshot.walkForward.summaries.map((item) => item.foldId)),
    ).sort((a, b) => a - b);
    const byVariant = new Map<string, Map<number, number | null>>();

    for (const item of snapshot.walkForward.summaries) {
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

  if (snapshot.walkForward.summaries.length === 0) {
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

export default function ResearchPanel({
  snapshot,
  loaded,
  error,
  theme,
}: ResearchPanelProps) {
  if (!loaded) {
    return (
      <section className="research-section" aria-labelledby="research-title">
        <div className="research-loading">策略研究快照加载中…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="research-section" aria-labelledby="research-title">
        <div className="research-section-head">
          <div>
            <p className="research-kicker">策略研究</p>
            <h2 id="research-title">牛门线全市场样本外研究</h2>
          </div>
        </div>
        <div className="error-box">research.json 加载失败：{error}</div>
      </section>
    );
  }

  if (!snapshot) {
    return (
      <section className="research-section" aria-labelledby="research-title">
        <div className="research-section-head">
          <div>
            <p className="research-kicker">策略研究</p>
            <h2 id="research-title">牛门线全市场样本外研究</h2>
            <p className="research-subtitle">
              当前部署尚未包含 <code>web/public/research.json</code>。从
              niu-men-line-strategy 导出版本化研究快照后，这里会自动展示。
            </p>
          </div>
        </div>
      </section>
    );
  }

  const mappingCoverage = snapshot.mapping.coverage.symbolCoverage;
  const warmup = snapshot.coverage.contextWarmup;

  return (
    <section className="research-section" aria-labelledby="research-title">
      <div className="research-section-head">
        <div>
          <p className="research-kicker">策略研究</p>
          <h2 id="research-title">牛门线全市场样本外研究</h2>
          <p className="research-subtitle">
            数据截止 {snapshot.source.dataDate} · 快照 {snapshot.generatedAt} · 映射口径{' '}
            {snapshot.mapping.confidence}
          </p>
        </div>
        <span className={`research-quality research-quality-${snapshot.quality.status}`}>
          {qualityLabel(snapshot)}
        </span>
      </div>

      <div className="research-kpi-grid">
        <div className="research-kpi">
          <span>评估覆盖</span>
          <strong>
            {snapshot.coverage.evaluatedSymbols.toLocaleString('zh-CN')} /{' '}
            {snapshot.coverage.requestedSymbols.toLocaleString('zh-CN')}
          </strong>
          <small>跳过 {snapshot.coverage.skippedSymbols.toLocaleString('zh-CN')} 只</small>
        </div>
        <div className="research-kpi">
          <span>行业代理</span>
          <strong>{snapshot.mapping.mappedProxyIndustryCodes}</strong>
          <small>
            股票映射覆盖 {mappingCoverage === null ? '—' : formatPercent(mappingCoverage, 1)}
          </small>
        </div>
        <div className="research-kpi">
          <span>上下文预热</span>
          <strong>{warmup.skippedSymbols.toLocaleString('zh-CN')}</strong>
          <small>因上下文 ready bar 不足跳过</small>
        </div>
        <div className="research-kpi">
          <span>滚动 OOS</span>
          <strong>
            {snapshot.walkForward.trainBars}/{snapshot.walkForward.testBars}/
            {snapshot.walkForward.stepBars}
          </strong>
          <small>训练 / 测试 / 步长 bar</small>
        </div>
      </div>

      <div className="research-card">
        <div className="research-card-head">
          <div>
            <h3>六变体 OOS 指标</h3>
            <p>指标按所有股票与样本外窗口记录汇总，展示中位数与成交约束计数。</p>
          </div>
        </div>
        <VariantTable variants={snapshot.variants} />
      </div>

      <div className="research-card">
        <div className="research-card-head">
          <div>
            <h3>滚动窗口年化收益中位数</h3>
            <p>{snapshot.walkForward.foldSemantics}</p>
          </div>
        </div>
        <RollingReturnChart snapshot={snapshot} theme={theme} />
      </div>

      <details className="research-details">
        <summary>覆盖、质量与成交约束详情</summary>
        <div className="research-detail-grid">
          <div>
            <h4>数据覆盖</h4>
            <p>
              上下文行 {formatCount(warmup.contextRows)}，ready 行 {formatCount(warmup.readyRows)}，
              warmup 行 {formatCount(warmup.warmupRows)}。
            </p>
            <p>规则：{warmup.rule || '—'}</p>
          </div>
          <div>
            <h4>质量检查</h4>
            <ul>
              <li>覆盖数量对账：{snapshot.quality.checks.coverageCountsReconcile ? '通过' : '警告'}</li>
              <li>六变体完整：{snapshot.quality.checks.expectedVariantsPresent ? '通过' : '警告'}</li>
              <li>fold key 唯一：{snapshot.quality.checks.foldKeysUnique ? '通过' : '警告'}</li>
              <li>OOS 记录非空：{snapshot.quality.checks.oosRowsPresent ? '通过' : '警告'}</li>
            </ul>
          </div>
          <div>
            <h4>执行时点</h4>
            <p>{snapshot.executionConstraints.timing || '—'}</p>
          </div>
        </div>
      </details>
    </section>
  );
}
