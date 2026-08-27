import type { EChartsType } from 'echarts';

export function downloadChartImage(chart: EChartsType, filename: string): void {
  const link = document.createElement('a');
  link.download = filename;
  link.href = chart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: 'transparent',
  });
  link.click();
}

