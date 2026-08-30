import {
  selectConditionalResearch,
  selectContextualResearch,
  type ConditionalResearchSnapshot,
  type ContextualResearchSnapshot,
} from '../contextualResearch.ts';

const ARCHETYPE_LABELS: Record<string, string> = {
  trend_up: '趋势上行',
  trend_down: '趋势下行',
  range: '区间',
  opening_drive_up: '开盘驱动上行',
  opening_drive_down: '开盘驱动下行',
  morning_reversal: '早盘反转',
  late_breakout: '尾盘突破',
  insufficient_data: '数据不足',
};

const TREND_LABELS: Record<string, string> = {
  up: '上行',
  down: '下行',
  flat: '平坦',
  insufficient_data: '数据不足',
};

const EVENT_LABELS: Record<string, string> = {
  cross_above: '向上穿越',
  cross_below: '向下穿越',
  reject_above: '上破后拒绝',
  reject_below: '下破后拒绝',
  reclaim_below: '上破后收回下方',
  reclaim_above: '下破后收回上方',
  break_and_hold_above: '突破并站稳上方',
  break_and_hold_below: '跌破并站稳下方',
};

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined || Number.isNaN(value)
    ? '—'
    : value.toFixed(2);
}

function formatPercent(value: number | null | undefined): string {
  return value === null || value === undefined || Number.isNaN(value)
    ? '—'
    : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

export default function ContextualResearchPanel({
  snapshot,
  instrumentCode,
  conditionalResearch = null,
}: {
  snapshot: ContextualResearchSnapshot;
  instrumentCode: string;
  conditionalResearch?: ConditionalResearchSnapshot | null;
}) {
  const { context, setupEvents, eventStudies } = selectContextualResearch(
    snapshot,
    instrumentCode,
  );

  if (!context) {
    return (
      <section className="workspace-panel contextual-research-panel">
        <div className="panel-heading compact">
          <div>
            <p className="section-kicker">条件研究</p>
            <h3>市场上下文与 Setup</h3>
          </div>
        </div>
        <p className="empty-panel">当前标的暂无上下文研究数据。</p>
      </section>
    );
  }

  const recentEvents = setupEvents.slice(0, 6);
  const recentStudies = eventStudies.slice(0, 3);
  const conditionalGroups = selectConditionalResearch(conditionalResearch, instrumentCode)
    .filter((group) => group.dimensions.strategyId === null)
    .slice(0, 8);
  const strategyConditionalGroups = selectConditionalResearch(conditionalResearch, instrumentCode)
    .filter((group) => group.dimensions.strategyId !== null)
    .slice(0, 8);

  return (
    <section
      className="workspace-panel contextual-research-panel"
      aria-labelledby="contextual-research-title"
    >
      <div className="panel-heading compact">
        <div>
          <p className="section-kicker">条件研究</p>
          <h3 id="contextual-research-title">市场上下文与 Setup</h3>
        </div>
        <span className="state-badge">
          {snapshot.quality.status === 'pass' ? '研究数据正常' : '研究数据警告'}
        </span>
      </div>

      <div className="contextual-section">
        <h4>背景与日型</h4>
        <dl className="state-metrics contextual-metrics">
          <div>
            <dt>20日背景</dt>
            <dd>
              {TREND_LABELS[context.higherTimeframe.trend20] ?? context.higherTimeframe.trend20}
              <small>20日收益 {formatPercent(context.higherTimeframe.return20)}</small>
            </dd>
          </div>
          <div>
            <dt>20日区间位置</dt>
            <dd>{formatPercent(context.higherTimeframe.rangePosition20)}</dd>
          </div>
          <div>
            <dt>日型</dt>
            <dd>{ARCHETYPE_LABELS[context.dayArchetype.id] ?? context.dayArchetype.id}</dd>
          </div>
          <div>
            <dt>Range / ATR</dt>
            <dd>{formatNumber(context.features.rangeToAtr)}</dd>
          </div>
          <div>
            <dt>收盘位置</dt>
            <dd>{formatPercent(context.features.closeLocation)}</dd>
          </div>
          <div>
            <dt>日内区间</dt>
            <dd>{formatPercent(context.features.intradayRangePct)}</dd>
          </div>
        </dl>
        <ul className="context-reasons">
          {context.dayArchetype.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      <div className="contextual-section">
        <h4>条件清单</h4>
        <div className="contextual-checklist">
          {[
            ['HTF 背景', context.higherTimeframe.trend20 !== 'insufficient_data'],
            ['日型已分类', context.dayArchetype.id !== 'insufficient_data'],
            ['Session 已分箱', context.sessions.length > 0],
            ['语义化参考位', context.referenceLevels.length > 0],
            ['跨市场观察', context.intermarket.length > 0],
          ].map(([label, available]) => (
            <div className="contextual-checklist-item" key={String(label)}>
              <span className={`checklist-state${available ? ' available' : ''}`} aria-hidden="true">
                {available ? '✓' : '—'}
              </span>
              <span>{label}</span>
              <small>{available ? '可用' : '数据不足'}</small>
            </div>
          ))}
        </div>
      </div>

      <div className="contextual-section">
        <h4>参考价位</h4>
        {context.referenceLevels.length === 0 ? (
          <p className="empty-panel">暂无语义化参考价位。</p>
        ) : (
          <ul className="key-level-list contextual-level-list">
            {context.referenceLevels.slice(0, 10).map((level) => (
              <li className="key-level-item" key={`${level.kind}-${level.value}`}>
                <span className="key-level-label">{level.sourceLabel}</span>
                <strong>
                  {formatNumber(level.value)}
                  <small>距当前价 {formatPercent(level.distancePct)}</small>
                </strong>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="contextual-section">
        <h4>Session 分箱</h4>
        {context.sessions.length === 0 ? (
          <p className="empty-panel">当前分时不足以生成 session 汇总。</p>
        ) : (
          <div className="contextual-table-wrap">
            <table className="contextual-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Return</th>
                  <th>Bars</th>
                </tr>
              </thead>
              <tbody>
                {context.sessions.map((session) => (
                  <tr key={session.id}>
                    <td>{session.id}</td>
                    <td>{formatNumber(session.high)}</td>
                    <td>{formatNumber(session.low)}</td>
                    <td>{formatPercent(session.returnPct)}</td>
                    <td>{session.bars}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="contextual-section">
        <h4>Setup 事件</h4>
        {recentEvents.length === 0 ? (
          <p className="empty-panel">当前分时没有检测到可记录的 setup 事件。</p>
        ) : (
          <div className="contextual-table-wrap">
            <table className="contextual-table">
              <thead>
                <tr>
                  <th>时间 / Session</th>
                  <th>事件</th>
                  <th>参考位</th>
                  <th>5m</th>
                  <th>30m</th>
                  <th>MFE / MAE</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.map((event, index) => (
                  <tr key={`${event.timestamp}-${event.eventType}-${index}`}>
                    <td>
                      {event.timestamp.slice(11, 16)}
                      <small>{event.session ?? '未归类'}</small>
                    </td>
                    <td>{EVENT_LABELS[event.eventType] ?? event.eventType}</td>
                    <td>
                      {event.referenceLevel.sourceLabel}
                      <small>{formatNumber(event.referenceLevel.value)}</small>
                    </td>
                    <td>{formatPercent(event.outcome.return5m)}</td>
                    <td>{formatPercent(event.outcome.return30m)}</td>
                    <td>
                      {formatPercent(event.outcome.mfe30m)} /{' '}
                      {formatPercent(event.outcome.mae30m)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="contextual-section">
        <h4>历史条件统计</h4>
        {conditionalGroups.length === 0 ? (
          <p className="empty-panel">尚未发布该标的的跨日条件统计。</p>
        ) : (
          <div className="contextual-table-wrap">
            <table className="contextual-table conditional-table">
              <thead>
                <tr>
                  <th>Session / 日型</th>
                  <th>Setup / 参考位</th>
                  <th>样本</th>
                  <th>胜率</th>
                  <th>Expectancy</th>
                  <th>MFE / MAE</th>
                </tr>
              </thead>
              <tbody>
                {conditionalGroups.map((group) => (
                  <tr
                    key={`${group.dimensions.session}-${group.dimensions.dayArchetype}-${group.dimensions.eventType}-${group.dimensions.referenceLevelKind}`}
                  >
                    <td>
                      {group.dimensions.session ?? '全部 Session'}
                      <small>{group.dimensions.dayArchetype ?? '全部日型'}</small>
                    </td>
                    <td>
                      {EVENT_LABELS[group.dimensions.eventType ?? ''] ?? group.dimensions.eventType ?? '全部事件'}
                      <small>{group.dimensions.referenceLevelKind ?? '全部参考位'}</small>
                    </td>
                    <td>{formatCount(group.metrics.sampleCount)}</td>
                    <td>{formatPercent(group.metrics.winRate)}</td>
                    <td>{formatPercent(group.metrics.expectancy)}</td>
                    <td>
                      {formatPercent(group.metrics.meanMfe)} / {formatPercent(group.metrics.meanMae)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {strategyConditionalGroups.length > 0 && (
        <div className="contextual-section">
          <h4>策略条件统计</h4>
          <div className="contextual-table-wrap">
            <table className="contextual-table conditional-table">
              <thead>
                <tr>
                  <th>策略 / 变体</th>
                  <th>Session / 日型</th>
                  <th>样本</th>
                  <th>胜率</th>
                  <th>Expectancy</th>
                </tr>
              </thead>
              <tbody>
                {strategyConditionalGroups.map((group) => (
                  <tr
                    key={`${group.dimensions.strategyId}-${group.dimensions.variantId}-${group.dimensions.session}-${group.dimensions.dayArchetype}`}
                  >
                    <td>
                      {group.dimensions.strategyId}
                      <small>{group.dimensions.variantId ?? '默认变体'}</small>
                    </td>
                    <td>
                      {group.dimensions.session ?? '全部 Session'}
                      <small>{group.dimensions.dayArchetype ?? '全部日型'}</small>
                    </td>
                    <td>{formatCount(group.metrics.sampleCount)}</td>
                    <td>{formatPercent(group.metrics.winRate)}</td>
                    <td>{formatPercent(group.metrics.expectancy)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="contextual-section">
        <h4>跨市场确认</h4>
        {context.intermarket.length === 0 ? (
          <p className="empty-panel">当前快照没有足够的重叠历史用于跨标的确认。</p>
        ) : (
          <dl className="state-metrics contextual-metrics">
            {context.intermarket.map((observation) => (
              <div key={observation.peer}>
                <dt>{observation.peer}</dt>
                <dd>
                  相关 {observation.correlation20.toFixed(2)}
                  <small>
                    相对强弱 {formatPercent(observation.relativeStrength20)} ·{' '}
                    {observation.relativeExtremeDivergence ? '极值背离' : '无极值背离'}
                  </small>
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {recentStudies.length > 0 && (
        <div className="contextual-section">
          <h4>事件研究</h4>
          <div className="contextual-table-wrap">
            <table className="contextual-table">
              <thead>
                <tr>
                  <th>事件</th>
                  <th>即时区间</th>
                  <th>+15m</th>
                  <th>+60m</th>
                  <th>MFE / MAE</th>
                </tr>
              </thead>
              <tbody>
                {recentStudies.map((study) => (
                  <tr key={study.event.id}>
                    <td>
                      {study.event.category}
                      <small>{study.event.importance}</small>
                    </td>
                    <td>{formatPercent(study.metrics.immediateRangePct)}</td>
                    <td>{formatPercent(study.metrics.return15m)}</td>
                    <td>{formatPercent(study.metrics.return60m)}</td>
                    <td>
                      {formatPercent(study.metrics.mfe60m)} /{' '}
                      {formatPercent(study.metrics.mae60m)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {snapshot.quality.warnings.length > 0 && (
        <details className="contextual-warnings">
          <summary>研究数据警告（{snapshot.quality.warnings.length}）</summary>
          <ul>
            {snapshot.quality.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
