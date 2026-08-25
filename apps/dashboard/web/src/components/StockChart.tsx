import { useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react/esm/core';
import type { EChartsOption } from 'echarts';
import type { StockData, LevelType } from '../types';
import { paletteFor, type ThemeMode } from '../theme';
import { echarts } from '../echarts';
import { visibleLevels } from '../priceLevels.ts';

export default function StockChart({
  stock,
  theme,
}: {
  stock: StockData;
  theme: ThemeMode;
}) {
  const [showAllLevels, setShowAllLevels] = useState(false);

  const option = useMemo<EChartsOption>(() => {
    const palette = paletteFor(theme);

    const levelColor: Record<LevelType, string> = {
      support: palette.levelSupport,
      resistance: palette.levelResistance,
      key: palette.levelKey,
      center: palette.levelCenter,
    };

    const dates = stock.daily.map((d) => d.date);
    // ECharts 蜡烛图数据顺序固定为 [open, close, low, high]，与直觉不同。
    const kdata = stock.daily.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = stock.daily.map((d) => ({
      value: d.volume,
      itemStyle: { color: d.close >= d.open ? palette.up : palette.down },
    }));

    const lastClose = stock.daily[stock.daily.length - 1]?.close ?? stock.indicators.lastClose;
    const markLineData = visibleLevels(stock.levels, lastClose, showAllLevels).map((l) => {
      const lineType: 'solid' | 'dashed' = l.type === 'center' ? 'dashed' : 'solid';
      const color = levelColor[l.type];
      return {
        yAxis: l.value,
        lineStyle: {
          color,
          type: lineType,
          width: 1.5,
        },
        label: {
          formatter: `${l.label} ${l.value.toFixed(2)}`,
          position: 'end' as const,
          color,
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
          axisLine: { lineStyle: { color: palette.axisLineColor } },
          axisLabel: { show: false },
          splitLine: { show: false },
          axisPointer: { label: { backgroundColor: palette.tooltipBg } },
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          boundaryGap: true,
          axisLine: { lineStyle: { color: palette.axisLineColor } },
          axisLabel: { show: true, fontSize: 10, color: palette.axisLabelColor },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          scale: true,
          gridIndex: 0,
          splitArea: { show: false },
          axisLine: { lineStyle: { color: palette.axisLineColor } },
          axisLabel: { fontSize: 10, color: palette.axisLabelColor },
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
            color: palette.up,
            color0: palette.down,
            borderColor: palette.up,
            borderColor0: palette.down,
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
  }, [showAllLevels, stock, theme]);

  return (
    <div className="stock-chart-shell">
      <div className="chart-control-row">
        <label>
          <input
            type="checkbox"
            aria-label="显示全部价位"
            checked={showAllLevels}
            onChange={(event) => setShowAllLevels(event.target.checked)}
          />
          显示全部价位
        </label>
        <span>默认仅标注最近支撑、阻力和关键结构</span>
      </div>
      <ReactECharts
        echarts={echarts}
        option={option}
        notMerge
        lazyUpdate
        style={{ height: 460, width: '100%' }}
      />
    </div>
  );
}
