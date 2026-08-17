import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { StockData } from '../types';

export default function IntradayChart({ stock }: { stock: StockData }) {
  const option = useMemo<EChartsOption | null>(() => {
    if (!stock.intraday || stock.intraday.length === 0) return null;

    const times = stock.intraday.map((d) => d.time.slice(11)); // 仅显示 HH:MM:SS
    const prices = stock.intraday.map((d) => d.price);
    const vwap = stock.indicators.vwap;

    return {
      animation: false,
      title: {
        text: `上一交易日分时（${stock.lastTradeDay}）`,
        left: 'center',
        textStyle: { fontSize: 13, color: '#555' },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: 56, right: 24, top: 36, bottom: 48 },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: { fontSize: 10, showMaxLabel: true },
        boundaryGap: false,
      },
      yAxis: {
        scale: true,
        axisLabel: { fontSize: 10 },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', bottom: 8, height: 16, start: 0, end: 100 },
      ],
      series: [
        {
          name: '价格',
          type: 'line',
          data: prices,
          showSymbol: false,
          smooth: false,
          lineStyle: { width: 1.5, color: '#1890ff' },
          markLine: vwap
            ? {
                silent: true,
                symbol: 'none',
                data: [
                  {
                    yAxis: vwap,
                    lineStyle: { color: '#fa8c16', type: 'dashed', width: 1.5 },
                    label: {
                      formatter: `VWAP ${vwap.toFixed(2)}`,
                      position: 'end',
                      color: '#fa8c16',
                      fontSize: 10,
                    },
                  },
                ],
              }
            : undefined,
        },
      ],
    };
  }, [stock]);

  if (!option) return null;
  return (
    <ReactECharts
      option={option}
      notMerge
      lazyUpdate
      style={{ height: 320, width: '100%' }}
    />
  );
}
