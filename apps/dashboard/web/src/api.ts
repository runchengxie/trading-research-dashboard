import type { DashboardData, ResearchSnapshot } from './types';
import { parseResearchSnapshot } from './researchSnapshot';

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

  // 部分静态托管会把缺失资源回退到 SPA 的 index.html，并返回 200。
  // 这种情况等价于“尚未部署研究快照”，不应让盘前与日内页面一起报错。
  const contentType = res.headers.get('content-type') ?? '';
  if (!contentType.toLowerCase().includes('application/json')) {
    return null;
  }

  return parseResearchSnapshot(await res.json());
}
