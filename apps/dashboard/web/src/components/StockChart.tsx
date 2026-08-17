import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { StockData, LevelType } from '../types';

const UP_COLOR = '#ef232a';
const DOWN_COLOR = '#14b143';

const LEVEL_COLOR: Record<LevelType, string> = {
  support: '#ef232a',
  resistance: '#14b143',
  key: '#fa8c16',
  center: '#722ed1',
};

export default function StockChart({ stock }: { stock: StockData }) {
  const option = useMemo<EChartsOption>(() => {
    const dates = stock.daily.map((d) => d.date);
    // ECharts 蜡烛图数据顺序固定为 [open, close, low, high]，与直觉不同。
    const kdata = stock.daily.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = stock.daily.map((d) => ({
      value: d.volume,
      itemStyle: { color: d.close >= d.open ? UP_COLOR : DOWN_COLOR },
    }));

    const markLineData = stock.levels.map((l) => {
      const lineType: 'solid' | 'dashed' = l.type === 'center' ? 'dashed' : 'solid';
      return {
        yAxis: l.value,
        lineStyle: {
          color: LEVEL_COLOR[l.type],
          type: lineType,
          width: 1.5,
        },
        label: {
          formatter: `${l.label} ${l.value.toFixed(2)}`,
          position: 'end' as const,
          color: LEVEL_COLOR[l.type],
          fontSize: 10,
        },
      };
    });

    return {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [
        { left: 56, right: 24, top: 24, height: '58%' },
        { left: 56, right: 24, top: '74%', height: '16%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          gridIndex: 0,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#888' } },
          axisLabel: { show: false },
          splitLine: { show: false },
          axisPointer: { label: { backgroundColor: '#6a7985' } },
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#888' } },
          axisLabel: { show: true, fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          scale: true,
          gridIndex: 0,
          splitArea: { show: false },
          axisLine: { lineStyle: { color: '#888' } },
          axisLabel: { fontSize: 10 },
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          bottom: 8,
          height: 16,
          start: 60,
          end: 100,
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: kdata,
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: {
            color: UP_COLOR,
            color0: DOWN_COLOR,
            borderColor: UP_COLOR,
            borderColor0: DOWN_COLOR,
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: markLineData,
          },
        },
        {
          name: '成交量',
          type: 'bar',
          data: volumes,
          xAxisIndex: 1,
          yAxisIndex: 1,
        },
      ],
    };
  }, [stock]);

  return (
    <ReactECharts
      option={option}
      notMerge
      lazyUpdate
      style={{ height: 460, width: '100%' }}
    />
  );
}
