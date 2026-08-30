import type { IndicatorValues } from '../types';

export type PrimaryIndicatorKey = 'vwap' | 'orbHigh' | 'orbLow';

export interface PrimaryIndicatorRow {
  key: PrimaryIndicatorKey;
  label: string;
  value: number | null;
}

export function primaryIndicatorRows(
  indicators: Pick<IndicatorValues, PrimaryIndicatorKey>,
): PrimaryIndicatorRow[] {
  return [
    { key: 'vwap', label: 'VWAP', value: indicators.vwap },
    { key: 'orbHigh', label: 'ORB突破上轨', value: indicators.orbHigh },
    { key: 'orbLow', label: 'ORB突破下轨', value: indicators.orbLow },
  ];
}
