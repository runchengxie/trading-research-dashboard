import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react/esm/core';
import type { EChartsOption } from 'echarts';
import type { StockData } from '../types';
import { paletteFor, type ThemeMode } from '../theme';
import { echarts } from '../echarts';

export default function IntradayChart({
  stock,
  theme,
}: {
  stock: StockData;
  theme: ThemeMode;
}) {
  const option = useMemo<EChartsOption | null>(() => {
    if (!stock.intraday || stock.intraday.length === 0) return null;

    const palette = paletteFor(theme);
    const times = stock.intraday.map((d) => d.time.slice(11)); // 仅显示 HH:MM:SS
    const prices = stock.intraday.map((d) => d.price);
    const vwap = stock.indicators.vwap;

    return {
      animation: false,
      title: {
        text: `上一交易日分时（${stock.lastTradeDay}）`,
        left: 'center',
        textStyle: { fontSize: 13, color: palette.titleColor },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: 56, right: 24, top: 36, bottom: 48 },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: {
          fontSize: 10,
          showMaxLabel: true,
          color: palette.axisLabelColor,
        },
        boundaryGap: false,
        axisLine: { lineStyle: { color: palette.axisLineColor } },
      },
      yAxis: {
        scale: true,
        axisLabel: { fontSize: 10, color: palette.axisLabelColor },
        axisLine: { lineStyle: { color: palette.axisLineColor } },
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
          lineStyle: { width: 1.5, color: palette.lineColor },
          markLine: vwap
            ? {
                silent: true,
                symbol: 'none',
                data: [
                  {
                    yAxis: vwap,
                    lineStyle: {
                      color: palette.vwapColor,
                      type: 'dashed',
                      width: 1.5,
                    },
                    label: {
                      formatter: `VWAP ${vwap.toFixed(2)}`,
                      position: 'end',
                      color: palette.vwapColor,
                      fontSize: 10,
                    },
                  },
                ],
              }
            : undefined,
        },
      ],
    };
  }, [stock, theme]);

  if (!option) return null;
  return (
    <ReactECharts
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height: 320, width: '100%' }}
    />
  );
}
