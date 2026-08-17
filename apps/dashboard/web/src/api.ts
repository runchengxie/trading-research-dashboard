import type { DashboardData } from './types';

export async function loadDashboard(): Promise<DashboardData> {
  const res = await fetch('./data.json');
  if (!res.ok) {
    throw new Error(`加载 data.json 失败：HTTP ${res.status}`);
  }
  return (await res.json()) as DashboardData;
}
