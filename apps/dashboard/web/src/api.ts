import type { DashboardData, ResearchSnapshot } from './types.ts';
import { parseResearchSnapshot } from './researchSnapshot.ts';
import type { StrategyDefinition } from './research/strategyRegistry.ts';
import type { StrategySnapshot } from './research/strategySnapshot.ts';

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

export type StrategyLoadStatus = 'available' | 'missing' | 'error';

export interface StrategyLoadResult {
  definition: StrategyDefinition;
  status: StrategyLoadStatus;
  snapshot: StrategySnapshot | null;
  error: string | null;
}

export async function loadStrategySnapshot(
  definition: StrategyDefinition,
  dashboardDate: string,
): Promise<StrategyLoadResult> {
  try {
    const res = await fetch(definition.snapshotPath);
    if (res.status === 404) {
      return { definition, status: 'missing', snapshot: null, error: null };
    }
    if (!res.ok) {
      throw new Error(`加载 ${definition.label} 研究快照失败：HTTP ${res.status}`);
    }

    const contentType = res.headers.get('content-type') ?? '';
    if (!contentType.toLowerCase().includes('application/json')) {
      return { definition, status: 'missing', snapshot: null, error: null };
    }

    if (definition.adapt === null) {
      throw new Error(`${definition.label} 研究快照适配器尚未发布`);
    }

    return {
      definition,
      status: 'available',
      snapshot: definition.adapt(await res.json(), dashboardDate),
      error: null,
    };
  } catch (error) {
    return {
      definition,
      status: 'error',
      snapshot: null,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}
