import { useEffect, useState } from 'react';

import {
  loadPlatformPublication,
  type PlatformPublicationLoadResult,
} from '../platformPublication.ts';

function shortCommit(value: string): string {
  return value.length > 12 ? value.slice(0, 12) : value;
}

export default function PlatformEvidencePanel() {
  const [result, setResult] = useState<PlatformPublicationLoadResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadPlatformPublication().then((loaded) => {
      if (!cancelled) setResult(loaded);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (result === null) {
    return (
      <section className="research-section" aria-labelledby="platform-evidence-title">
        <div className="research-loading">平台研究证据清单加载中…</div>
      </section>
    );
  }

  if (result.status === 'missing') {
    return (
      <section className="research-section" aria-labelledby="platform-evidence-title">
        <div className="research-section-head">
          <div>
            <p className="research-kicker">研究证据</p>
            <h2 id="platform-evidence-title">平台发布证据</h2>
            <p className="research-subtitle">
              当前静态部署没有 platform-publication.json。行情和已有策略快照继续正常工作。
            </p>
          </div>
        </div>
        <div className="research-empty" role="status">
          workspace 尚未向本次 Dashboard 构建发布统一研究证据包。
        </div>
      </section>
    );
  }

  if (result.status === 'error') {
    return (
      <section className="research-section" aria-labelledby="platform-evidence-title">
        <div className="research-section-head">
          <div>
            <p className="research-kicker">研究证据</p>
            <h2 id="platform-evidence-title">平台发布证据</h2>
          </div>
        </div>
        <div className="research-empty strategy-unavailable" role="status">
          <strong>平台研究证据清单校验失败</strong>
          <p>{result.error}</p>
        </div>
      </section>
    );
  }

  const publication = result.publication;
  return (
    <section className="research-section" aria-labelledby="platform-evidence-title">
      <div className="research-section-head">
        <div>
          <p className="research-kicker">研究证据</p>
          <h2 id="platform-evidence-title">平台发布证据</h2>
          <p className="research-subtitle">
            这里只展示 workspace 明确投影给公开 Dashboard 的研究产物，不在浏览器重新计算研究指标。
          </p>
        </div>
        <div className="research-status-group">
          <span className="research-quality research-quality-pass">公开投影已校验</span>
        </div>
      </div>

      <div className="research-kpi-grid">
        <div className="research-kpi">
          <span>Producer</span>
          <strong>{publication.producerRepository}</strong>
          <small>commit {shortCommit(publication.producerCommit)}</small>
        </div>
        <div className="research-kpi">
          <span>Research run</span>
          <strong>{publication.runId}</strong>
          <small>{publication.generatedAt}</small>
        </div>
        <div className="research-kpi">
          <span>公开研究产物</span>
          <strong>{publication.artifacts.length}</strong>
          <small>只包含显式授权给 Dashboard 的 public projection</small>
        </div>
        <div className="research-kpi">
          <span>运行方式</span>
          <strong>静态快照</strong>
          <small>GitHub Pages / Workers 无需 research runtime</small>
        </div>
      </div>

      <div className="research-card">
        <div className="research-card-head">
          <div>
            <h3>发布产物清单</h3>
            <p>SHA-256 在构建阶段已经核对；页面保留 schema、来源和内容身份用于审计。</p>
          </div>
        </div>
        <div className="research-table-wrap">
          <table className="research-table">
            <thead>
              <tr>
                <th>Artifact</th>
                <th>Schema</th>
                <th>Media type</th>
                <th>SHA-256</th>
                <th>静态文件</th>
              </tr>
            </thead>
            <tbody>
              {publication.artifacts.map((artifact) => (
                <tr key={artifact.artifactId}>
                  <td>
                    <span className="research-variant-label">{artifact.artifactId}</span>
                  </td>
                  <td><code>{artifact.schemaVersion}</code></td>
                  <td>{artifact.mediaType}</td>
                  <td><code>{artifact.sha256.slice(0, 12)}…</code></td>
                  <td>
                    <a href={`./platform/${artifact.relativePath}`} target="_blank" rel="noreferrer">
                      查看投影
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
