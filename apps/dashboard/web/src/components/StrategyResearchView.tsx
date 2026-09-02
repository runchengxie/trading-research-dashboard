import type { StrategyLoadResult } from '../api.ts';
import type { ThemeMode } from '../theme';
import PlatformEvidencePanel from './PlatformEvidencePanel';
import ResearchPanel from './ResearchPanel';
import StrategyComparisonPanel from './StrategyComparisonPanel';

type ResearchTab = string;

interface StrategyResearchViewProps {
  results: StrategyLoadResult[];
  loaded: boolean;
  activeTab: ResearchTab;
  onTabChange: (tab: ResearchTab) => void;
  theme: ThemeMode;
}

function StrategyUnavailable({ result }: { result: StrategyLoadResult }) {
  const snapshotName = result.definition.snapshotPath.split('/').pop() ?? result.definition.snapshotPath;
  return (
    <section className="research-section" aria-labelledby="research-title">
      <div className="research-section-head">
        <div>
          <p className="research-kicker">策略研究</p>
          <h2 id="research-title">{result.definition.label}研究</h2>
          <p className="research-subtitle">{result.definition.description}</p>
        </div>
      </div>
      <div className="research-empty strategy-unavailable" role="status">
        <strong>
          {result.status === 'missing' ? '尚无已发布研究快照' : '研究快照加载失败'}
        </strong>
        <p>
          {result.status === 'missing'
            ? `当前部署尚未包含 ${result.definition.snapshotPath}，该策略不会影响其他研究和行情区域。`
            : `${snapshotName} 加载失败：${result.error}`}
        </p>
      </div>
    </section>
  );
}

export default function StrategyResearchView({
  results,
  loaded,
  activeTab,
  onTabChange,
  theme,
}: StrategyResearchViewProps) {
  if (!loaded) {
    return (
      <section className="research-section" aria-labelledby="research-title">
        <div className="research-loading">策略研究快照加载中…</div>
      </section>
    );
  }

  const evidenceTab = 'platform-evidence';
  const comparisonTab = 'comparison';
  const selectedResult = results.find((result) => result.definition.id === activeTab);

  return (
    <section className="strategy-research-view" aria-label="策略研究工作区">
      <nav className="research-tabs" aria-label="策略研究子页面">
        {results.map((result) => (
          <button
            type="button"
            className={`research-tab${activeTab === result.definition.id ? ' active' : ''}`}
            aria-selected={activeTab === result.definition.id}
            key={result.definition.id}
            onClick={() => onTabChange(result.definition.id)}
          >
            {result.definition.label}
            <span className={`research-tab-status research-tab-status-${result.status}`}>
              {result.status === 'available' ? '已发布' : result.status === 'missing' ? '待发布' : '异常'}
            </span>
          </button>
        ))}
        <button
          type="button"
          className={`research-tab${activeTab === evidenceTab ? ' active' : ''}`}
          aria-selected={activeTab === evidenceTab}
          onClick={() => onTabChange(evidenceTab)}
        >
          研究证据
        </button>
        <button
          type="button"
          className={`research-tab${activeTab === comparisonTab ? ' active' : ''}`}
          aria-selected={activeTab === comparisonTab}
          onClick={() => onTabChange(comparisonTab)}
        >
          策略对比
        </button>
      </nav>

      {activeTab === evidenceTab ? (
        <PlatformEvidencePanel />
      ) : activeTab === comparisonTab ? (
        <StrategyComparisonPanel results={results} />
      ) : selectedResult?.status === 'available' && selectedResult.snapshot ? (
        <ResearchPanel snapshot={selectedResult.snapshot} theme={theme} />
      ) : selectedResult ? (
        <StrategyUnavailable result={selectedResult} />
      ) : (
        <div className="research-empty">当前没有可用的策略研究入口。</div>
      )}
    </section>
  );
}
