export interface AgentPortfolioPosition {
  symbol: string;
  shares: number;
  price: number;
  marketValue: number;
  weight: number;
}

export interface AgentPortfolioTrade {
  timestamp: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  shares: number;
  price: number;
  fee: number;
}

export interface AgentPortfolioHistoryPoint {
  asOf: string;
  equity: number;
  nav: number;
  drawdown: number;
}

export interface AgentPortfolioLatest {
  schemaVersion: 'trading_research.agent_portfolio.v1';
  generatedAt: string;
  asOf: string;
  agent: {
    id: string;
    provider: string;
    model: string;
    promptVersion: string;
    inputHash: string;
  };
  portfolio: {
    initialEquity: number;
    equity: number;
    cash: number;
    nav: number;
    totalReturn: number;
    maxDrawdown: number;
  };
  metrics: { totalReturn: number; maxDrawdown: number };
  decision: { targetWeights: Record<string, number>; reasoningSummary: string };
  positions: AgentPortfolioPosition[];
  trades: AgentPortfolioTrade[];
  history: AgentPortfolioHistoryPoint[];
}

export const A_SHARE_INSTRUMENT_NAMES: Readonly<Record<string, string>> = {
  '159915.SZ': '创业板ETF',
  '510300.SH': '沪深300ETF',
  '511010.SH': '国债ETF',
  '512100.SH': '中证1000ETF',
  '600519.SH': '贵州茅台',
  '000858.SZ': '五粮液',
  '601318.SH': '中国平安',
  '600036.SH': '招商银行',
  '300750.SZ': '宁德时代',
};

export function displayInstrument(symbol: string): string {
  const name = A_SHARE_INSTRUMENT_NAMES[symbol];
  return name ? `${symbol} · ${name}` : symbol;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function hasFiniteNumbers(value: Record<string, unknown>, keys: string[]): boolean {
  return keys.every((key) => isFiniteNumber(value[key]));
}

function numberField(value: Record<string, unknown>, key: string): number {
  const field = value[key];
  if (!isFiniteNumber(field)) throw new Error('Agent 组合快照字段无效');
  return field;
}

export function parseAgentPortfolio(value: unknown): AgentPortfolioLatest {
  if (!isRecord(value) || value.schemaVersion !== 'trading_research.agent_portfolio.v1') {
    throw new Error('不支持的 Agent 组合快照版本');
  }
  const agent = value.agent;
  const portfolio = value.portfolio;
  const metrics = value.metrics;
  const decision = value.decision;
  const positions = value.positions;
  const trades = value.trades;
  const history = value.history;
  if (
    !isNonEmptyString(value.generatedAt) ||
    !isIsoDate(value.asOf) ||
    !isRecord(agent) ||
    !isRecord(portfolio) ||
    !isRecord(metrics) ||
    !isRecord(decision) ||
    !Array.isArray(positions) ||
    !Array.isArray(trades) ||
    !Array.isArray(history) ||
    !hasFiniteNumbers(portfolio, ['initialEquity', 'equity', 'cash', 'nav', 'totalReturn', 'maxDrawdown']) ||
    !hasFiniteNumbers(metrics, ['totalReturn', 'maxDrawdown']) ||
    !isNonEmptyString(decision.reasoningSummary) ||
    !isRecord(decision.targetWeights) ||
    !isNonEmptyString(agent.id) ||
    !isNonEmptyString(agent.provider) ||
    !isNonEmptyString(agent.model) ||
    !isNonEmptyString(agent.promptVersion) ||
    typeof agent.inputHash !== 'string' ||
    !/^[0-9a-f]{64}$/.test(agent.inputHash)
  ) {
    throw new Error('Agent 组合快照字段无效');
  }
  const targetWeights: Record<string, number> = {};
  for (const [symbol, weight] of Object.entries(decision.targetWeights)) {
    if (!isFiniteNumber(weight) || weight < 0 || weight > 1) throw new Error('Agent 组合快照字段无效');
    targetWeights[symbol] = weight;
  }
  if (
    Math.abs(Object.values(targetWeights).reduce((sum, weight) => sum + weight, 0) - 1) > 1e-6 ||
    !positions.every(isValidPosition) ||
    !trades.every(isValidTrade) ||
    !history.every(isValidHistory)
  ) {
    throw new Error('Agent 组合快照字段无效');
  }
  return {
    schemaVersion: value.schemaVersion,
    generatedAt: value.generatedAt,
    asOf: value.asOf,
    agent: {
      id: agent.id,
      provider: agent.provider,
      model: agent.model,
      promptVersion: agent.promptVersion,
      inputHash: agent.inputHash,
    },
    portfolio: {
      initialEquity: numberField(portfolio, 'initialEquity'),
      equity: numberField(portfolio, 'equity'),
      cash: numberField(portfolio, 'cash'),
      nav: numberField(portfolio, 'nav'),
      totalReturn: numberField(portfolio, 'totalReturn'),
      maxDrawdown: numberField(portfolio, 'maxDrawdown'),
    },
    metrics: {
      totalReturn: numberField(metrics, 'totalReturn'),
      maxDrawdown: numberField(metrics, 'maxDrawdown'),
    },
    decision: { targetWeights, reasoningSummary: decision.reasoningSummary },
    positions: positions as AgentPortfolioPosition[],
    trades: trades as AgentPortfolioTrade[],
    history: history as AgentPortfolioHistoryPoint[],
  };
}

function isValidPosition(value: unknown): value is AgentPortfolioPosition {
  return isRecord(value) && isNonEmptyString(value.symbol) && isIntegerAtLeast(value.shares, 0) &&
    isFiniteNumber(value.price) && value.price > 0 && isFiniteNumber(value.marketValue) && value.marketValue >= 0 &&
    isFiniteNumber(value.weight) && value.weight >= 0 && value.weight <= 1;
}

function isValidTrade(value: unknown): value is AgentPortfolioTrade {
  return isRecord(value) && isNonEmptyString(value.timestamp) && isNonEmptyString(value.symbol) &&
    (value.side === 'BUY' || value.side === 'SELL') && isIntegerAtLeast(value.shares, 1) &&
    isFiniteNumber(value.price) && value.price > 0 && isFiniteNumber(value.fee) && value.fee >= 0;
}

function isValidHistory(value: unknown): value is AgentPortfolioHistoryPoint {
  return isRecord(value) && isIsoDate(value.asOf) && isFiniteNumber(value.equity) && value.equity >= 0 &&
    isFiniteNumber(value.nav) && value.nav >= 0 && isFiniteNumber(value.drawdown) && value.drawdown <= 0;
}

function isIntegerAtLeast(value: unknown, minimum: number): value is number {
  return isFiniteNumber(value) && Number.isInteger(value) && value >= minimum;
}

export async function loadAgentPortfolio(path = 'agent/latest.json'): Promise<AgentPortfolioLatest> {
  const normalizedPath = path.replace(/^\/+/, '');
  const response = await fetch(normalizedPath);
  if (!response.ok) throw new Error(`Agent 组合快照加载失败：HTTP ${response.status}`);
  return parseAgentPortfolio(await response.json());
}
