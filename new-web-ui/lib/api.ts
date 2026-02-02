/**
 * 백엔드 API 클라이언트. NEXT_PUBLIC_API_URL (기본 http://localhost:8080)
 */

const getBaseUrl = () =>
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080")
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface CommitListItem {
  id: number;
  trader: string;
  periodStart: string; // ISO instant
  periodEnd: string;
  totalPnl: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  tradeCount: number;
  hash: string;
  txHash: string | null;
  timestamp: number;
  verified: boolean;
}

export interface PerformanceSummaryResponse {
  summary: {
    accountId: string;
    strategyTag: string;
    period_start: string;
    period_end: string;
    total_pnl: number;
    max_drawdown: number;
    sharpe_ratio: number;
    equity_curve_sampled: number[];
  };
  hashHex: string;
  txHash: string | null;
  winRate?: number;
  tradeCount?: number;
  verified?: boolean;
}

export interface TradeResponse {
  id: number;
  accountId: string;
  tradeDate: string;
  symbol: string;
  side: string;
  qty: number;
  price: number;
  fee: number;
  orderId: string | null;
  execId: string | null;
  strategyTag: string | null;
}

export async function fetchCommits(accountId?: string, limit = 50): Promise<CommitListItem[]> {
  const url = new URL(`${getBaseUrl()}/api/performance/commits`);
  url.searchParams.set("limit", String(limit));
  if (accountId) url.searchParams.set("accountId", accountId);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch commits");
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchPerformanceSummary(
  accountId: string,
  start: string,
  end: string,
  strategyTag?: string
): Promise<PerformanceSummaryResponse> {
  const url = new URL(`${getBaseUrl()}/api/performance/summary`);
  url.searchParams.set("accountId", accountId);
  url.searchParams.set("start", start);
  url.searchParams.set("end", end);
  if (strategyTag) url.searchParams.set("strategyTag", strategyTag);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

export async function fetchTrades(
  accountId: string,
  start: string,
  end: string,
  strategyTag?: string
): Promise<TradeResponse[]> {
  const url = new URL(`${getBaseUrl()}/api/trades`);
  url.searchParams.set("accountId", accountId);
  url.searchParams.set("start", start);
  url.searchParams.set("end", end);
  if (strategyTag) url.searchParams.set("strategyTag", strategyTag);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch trades");
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/** 백엔드 CommitListItem → UI PerformanceSummary */
export function commitToPerformanceSummary(c: CommitListItem): import("./types").PerformanceSummary {
  return {
    id: String(c.id),
    trader: c.trader,
    periodStart: new Date(c.periodStart).toISOString().split("T")[0],
    periodEnd: new Date(c.periodEnd).toISOString().split("T")[0],
    totalPnl: c.totalPnl,
    maxDrawdown: c.maxDrawdown,
    sharpeRatio: c.sharpeRatio,
    winRate: c.winRate,
    tradeCount: c.tradeCount,
    hash: c.hash,
    txHash: c.txHash ?? "",
    timestamp: c.timestamp,
    verified: c.verified,
  };
}

/** summary.equity_curve_sampled + period_start → { date, value }[] */
export function equityCurveFromSummary(
  periodStart: string,
  sampled: number[]
): { date: string; value: number }[] {
  const start = new Date(periodStart);
  return sampled.map((value, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return { date: d.toISOString().split("T")[0], value };
  });
}

/** 백엔드 TradeResponse → UI Trade (단일 체결 기준 PnL) */
export function tradeResponseToTrade(t: TradeResponse): import("./types").Trade {
  const notional = t.price * t.qty;
  const fee = t.fee ?? 0;
  const pnl =
    t.side.toUpperCase() === "SELL" ? notional - fee : -notional - fee;
  return {
    id: String(t.id),
    symbol: t.symbol,
    side: t.side.toUpperCase() as "BUY" | "SELL",
    qty: t.qty,
    entryPrice: t.price,
    exitPrice: t.price,
    pnl,
    date: t.tradeDate.split("T")[0],
  };
}

/** 상세용: summary + trades → topWins, topLosses (PnL 기준 정렬) */
export function buildTopWinsLosses(
  trades: TradeResponse[],
  topN = 3
): { topWins: import("./types").Trade[]; topLosses: import("./types").Trade[] } {
  const mapped = trades.map(tradeResponseToTrade);
  const sorted = [...mapped].sort((a, b) => b.pnl - a.pnl);
  const topWins = sorted.filter((t) => t.pnl > 0).slice(0, topN);
  const topLosses = sorted.filter((t) => t.pnl < 0).slice(-topN).reverse();
  return { topWins, topLosses };
}
