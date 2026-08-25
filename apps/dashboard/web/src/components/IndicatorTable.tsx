import type { IndicatorValues, StockData } from '../types';

const INDICATOR_ROWS: { key: keyof IndicatorValues; label: string }[] = [
  { key: 'lastClose', label: '最新收盘价' },
  { key: 'atr20', label: '20日ATR' },
  { key: 'support', label: '聚类支撑位' },
  { key: 'resistance', label: '聚类阻力位' },
  { key: 'nearestKeyLevel', label: '最近关键价格' },
  { key: 'yesterdayLow', label: '昨低（关键支撑）' },
  { key: 'yesterdayHigh', label: '昨高（关键阻力）' },
  { key: 'vwap', label: '上一日VWAP' },
  { key: 'vwapDev', label: '收盘相对VWAP偏离' },
  { key: 'vwapDevThreshold', label: 'VWAP_DEV阈值' },
  { key: 'orbHigh', label: 'ORB突破上轨' },
  { key: 'orbLow', label: 'ORB突破下轨' },
];

function fmt(v: number | null): string {
  return v === null || Number.isNaN(v) ? '—' : v.toFixed(2);
}

export default function IndicatorTable({ stock }: { stock: StockData }) {
  const ind = stock.indicators;
  const usageNotes = stock.usageNotes ?? [];
  return (
    <div className="indicator-block">
      <table className="indicator-table">
        <tbody>
          {INDICATOR_ROWS.map((r) => (
            <tr key={r.key}>
              <th>{r.label}</th>
              <td className={ind[r.key] === null ? 'muted' : ''}>{fmt(ind[r.key])}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {usageNotes.length > 0 && (
        <div className="usage-notes">
          <h4>使用说明</h4>
          <ul>
            {usageNotes.map((n, i) => (
              <li key={`${n.param}-${i}`}>
                <span className="note-param">{n.param}</span>
                <span className="note-text">{n.note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
