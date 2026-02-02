export interface PerformanceSummary {
  id: string;
  trader: string;
  periodStart: string;
  periodEnd: string;
  totalPnl: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  tradeCount: number;
  hash: string;
  txHash: string;
  timestamp: number;
  verified: boolean;
}

export interface PerformanceDetail extends PerformanceSummary {
  equityCurve: { date: string; value: number }[];
  dailyReturns: { date: string; return: number }[];
  monthlyReturns: { month: string; return: number }[];
  topWins: Trade[];
  topLosses: Trade[];
}

export interface Trade {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  date: string;
}

export interface HashVerificationResult {
  isValid: boolean;
  computedHash: string;
  onChainHash: string;
  message: string;
}

export type TabType = "dashboard" | "verify" | "detail";
