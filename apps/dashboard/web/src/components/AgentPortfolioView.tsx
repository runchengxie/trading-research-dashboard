import { useEffect, useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react/esm/core';
import { echarts } from '../echarts';
import { displayInstrument, loadAgentPortfolio, type AgentPortfolioLatest } from '../agentPortfolio';
import { Button } from './ui/button';

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

function PortfolioChart({ snapshot }: { snapshot: AgentPortfolioLatest }) {
  const option = useMemo(() => ({
    animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 20, top: 20, bottom: 36 },
    xAxis: { type: 'category', data: snapshot.history.map((point) => point.asOf) },
    yAxis: { type: 'value', scale: true },
    series: [{
      name: 'NAV',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: snapshot.history.map((point) => Number(point.nav.toFixed(6))),
      lineStyle: { color: '#1267d6', width: 3 },
      itemStyle: { color: '#1267d6' },
    }],
  }), [snapshot.history]);

  return <ReactECharts echarts={echarts} option={option} notMerge lazyUpdate style={{ width: '100%', height: 320 }} />;
}

export default function AgentPortfolioView() {
  const [snapshot, setSnapshot] = useState<AgentPortfolioLatest | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    loadAgentPortfolio().then(setSnapshot).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : String(reason));
    });
  };

  useEffect(load, []);

  if (error) {
    return (
      <section className="agent-portfolio-section" aria-labelledby="agent-portfolio-title">
        <div className="section-heading">
          <div><p className="section-kicker">纸面交易实验</p><h2 id="agent-portfolio-title">Agent Portfolio</h2></div>
          <Button variant="outline" size="sm" onClick={load}>重新加载</Button>
        </div>
        <div className="empty-market-state" role="status">当前没有可用的 Agent 组合快照：{error}</div>
      </section>
    );
  }

  if (!snapshot) {
    return <section className="agent-portfolio-section" aria-labelledby="agent-portfolio-title"><div className="research-loading">Agent 组合快照加载中…</div></section>;
  }

  return (
    <section className="agent-portfolio-section" aria-labelledby="agent-portfolio-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">纸面交易实验</p>
          <h2 id="agent-portfolio-title">Agent Portfolio</h2>
          <p className="section-subtitle">{snapshot.agent.model} · 数据日期：{snapshot.asOf} · 仅用于研究</p>
        </div>
        <span className="data-status"><span className="data-status-dot" aria-hidden="true" />最近更新：{snapshot.generatedAt}</span>
      </div>

      <div className="agent-metric-grid">
        <div className="agent-metric-card"><span>组合权益</span><strong>{formatUsd(snapshot.portfolio.equity)}</strong></div>
        <div className="agent-metric-card"><span>NAV</span><strong>{snapshot.portfolio.nav.toFixed(4)}</strong></div>
        <div className="agent-metric-card"><span>累计收益</span><strong className={snapshot.portfolio.totalReturn >= 0 ? 'up' : 'down'}>{formatPercent(snapshot.portfolio.totalReturn)}</strong></div>
        <div className="agent-metric-card"><span>最大回撤</span><strong className="down">{formatPercent(snapshot.portfolio.maxDrawdown)}</strong></div>
      </div>

      <div className="agent-portfolio-grid">
        <div className="agent-panel agent-chart-panel"><h3>净值曲线</h3><PortfolioChart snapshot={snapshot} /></div>
        <div className="agent-panel"><h3>当前持仓</h3><dl className="agent-position-list">
          <div><dt>现金</dt><dd>{formatUsd(snapshot.portfolio.cash)}</dd></div>
          {snapshot.positions.map((position) => <div key={position.symbol}><dt>{displayInstrument(position.symbol)}</dt><dd>{position.shares} 股 · {formatPercent(position.weight)}</dd></div>)}
        </dl></div>
      </div>

      <div className="agent-panel agent-decision-panel"><h3>最近一次决策</h3><p>{snapshot.decision.reasoningSummary}</p><div className="agent-weight-list">{Object.entries(snapshot.decision.targetWeights).map(([symbol, weight]) => <span key={symbol}><b>{displayInstrument(symbol)}</b> {formatPercent(weight)}</span>)}</div></div>

      <div className="agent-panel"><h3>最近成交</h3>{snapshot.trades.length === 0 ? <p className="section-subtitle">本次没有调仓。</p> : <div className="agent-trade-list">{snapshot.trades.map((trade, index) => <div key={`${trade.timestamp}-${trade.symbol}-${index}`}><span>{trade.timestamp}</span><b className={trade.side === 'BUY' ? 'up' : 'down'}>{trade.side}</b><span>{displayInstrument(trade.symbol)} · {trade.shares} 股 · {formatUsd(trade.price)}</span></div>)}</div>}</div>
    </section>
  );
}
