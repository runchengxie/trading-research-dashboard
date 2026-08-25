import type { DashboardData, ResearchSnapshot } from './types';

export async function loadDashboard(): Promise<DashboardData> {
  const res = await fetch('./data.json');
  if (!res.ok) {
    throw new Error(`加载 data.json 失败：HTTP ${res.status}`);
  }
  return (await res.json()) as DashboardData;
}

export async function loadResearch(): Promise<ResearchSnapshot | null> {
  const res = await fetch('./research.json');
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`加载 research.json 失败：HTTP ${res.status}`);
  }
  const payload = (await res.json()) as Partial<ResearchSnapshot>;
  if (payload.schemaVersion !== 'niu_men.research_snapshot.v1') {
    throw new Error(`不支持的研究快照版本：${String(payload.schemaVersion ?? 'missing')}`);
  }
  return payload as ResearchSnapshot;
}
