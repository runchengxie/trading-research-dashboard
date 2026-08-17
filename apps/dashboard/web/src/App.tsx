import { useEffect, useState } from 'react';
import { loadDashboard } from './api';
import type { DashboardData } from './types';
import StockChart from './components/StockChart';
import IntradayChart from './components/IntradayChart';
import IndicatorTable from './components/IndicatorTable';

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <div className="container">
        <div className="error-box">
          加载失败：{error}
          <br />
          请先运行 <code>uv run python astock_tech.py --json web/public/data.json</code> 生成数据。
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container">
        <div className="loading">加载中…</div>
      </div>
    );
  }

  return (
    <div className="container">
      <header className="page-header">
        <h1>A股 T+0 交易仪表盘</h1>
        <p className="subtitle">数据日期：{data.generatedAt}</p>
      </header>

      {data.stocks.length === 0 && (
        <div className="error-box">本期没有成功处理的股票。</div>
      )}

      <div className="stock-grid">
        {data.stocks.map((stock) => (
          <section className="stock-card" key={stock.code}>
            <div className="stock-card-head">
              <div>
                <h2>
                  {stock.name} <span className="code">{stock.code}</span>
                </h2>
                <p className="meta">
                  {stock.tradingStyle} · 最近交易日 {stock.lastTradeDay}
                </p>
              </div>
            </div>

            <StockChart stock={stock} />
            <div className="panel-row">
              <IndicatorTable stock={stock} />
            </div>
            <IntradayChart stock={stock} />
          </section>
        ))}
      </div>

      <footer className="page-footer">
        数据来源：akshare / tushare · 仅供研究，不构成投资建议
      </footer>
    </div>
  );
}
