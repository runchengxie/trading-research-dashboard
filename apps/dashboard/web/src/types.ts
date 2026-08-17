export interface DailyBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IntradayBar {
  time: string;
  price: number;
  volume: number;
}

export type LevelType = 'support' | 'resistance' | 'key' | 'center';

export interface Level {
  type: LevelType;
  value: number;
  label: string;
}

export interface IndicatorValues {
  lastClose: number | null;
  atr20: number | null;
  support: number | null;
  resistance: number | null;
  nearestKeyLevel: number | null;
  yesterdayLow: number | null;
  yesterdayHigh: number | null;
  vwap: number | null;
  vwapDev: number | null;
  vwapDevThreshold: number | null;
  orbHigh: number | null;
  orbLow: number | null;
}

export interface UsageNote {
  param: string;
  note: string;
}

export interface StockData {
  code: string;
  name: string;
  tradingStyle: string;
  lastTradeDay: string;
  indicators: IndicatorValues;
  levels: Level[];
  daily: DailyBar[];
  intraday: IntradayBar[] | null;
  usageNotes: UsageNote[];
}

export interface DashboardData {
  generatedAt: string;
  stocks: StockData[];
}
