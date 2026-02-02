import type { PerformanceSummary, PerformanceDetail } from "./types";

export const mockPerformances: PerformanceSummary[] = [
  {
    id: "1",
    trader: "0x742d35Cc6634C0532925a3b844Bc9e7595f3a71d",
    periodStart: "2025-01-01",
    periodEnd: "2025-01-31",
    totalPnl: 15.42,
    maxDrawdown: -8.21,
    sharpeRatio: 1.85,
    winRate: 62.5,
    tradeCount: 48,
    hash: "0x8a7b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7890",
    txHash: "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    timestamp: 1706745600000,
    verified: true,
  },
  {
    id: "2",
    trader: "0x742d35Cc6634C0532925a3b844Bc9e7595f3a71d",
    periodStart: "2025-02-01",
    periodEnd: "2025-02-28",
    totalPnl: -3.25,
    maxDrawdown: -12.45,
    sharpeRatio: 0.45,
    winRate: 45.0,
    tradeCount: 35,
    hash: "0x9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c",
    txHash: "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    timestamp: 1709251200000,
    verified: true,
  },
  {
    id: "3",
    trader: "0x8ba1f109551bD432803012645Ac136ddd64DBA72",
    periodStart: "2025-03-01",
    periodEnd: "2025-03-31",
    totalPnl: 28.67,
    maxDrawdown: -5.32,
    sharpeRatio: 2.45,
    winRate: 71.2,
    tradeCount: 52,
    hash: "0xabc123def456789abc123def456789abc123def456789abc123def456789abc1",
    txHash: "0x567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234",
    timestamp: 1711929600000,
    verified: false,
  },
];

function generateEquityCurve(): { date: string; value: number }[] {
  const curve: { date: string; value: number }[] = [];
  let value = 10000000;
  const startDate = new Date("2025-01-01");

  for (let i = 0; i < 30; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    value = value * (1 + (Math.random() * 0.04 - 0.015));
    curve.push({
      date: date.toISOString().split("T")[0],
      value: Math.round(value),
    });
  }

  return curve;
}

function generateMonthlyReturns(): { month: string; return: number }[] {
  return [
    { month: "1월", return: 5.2 },
    { month: "2월", return: -2.1 },
    { month: "3월", return: 8.4 },
    { month: "4월", return: 3.7 },
    { month: "5월", return: -1.5 },
    { month: "6월", return: 6.8 },
  ];
}

export const mockPerformanceDetail: PerformanceDetail = {
  ...mockPerformances[0],
  equityCurve: generateEquityCurve(),
  dailyReturns: [],
  monthlyReturns: generateMonthlyReturns(),
  topWins: [
    {
      id: "t1",
      symbol: "삼성전자",
      side: "BUY",
      qty: 100,
      entryPrice: 71500,
      exitPrice: 78200,
      pnl: 670000,
      date: "2025-01-15",
    },
    {
      id: "t2",
      symbol: "SK하이닉스",
      side: "BUY",
      qty: 50,
      entryPrice: 185000,
      exitPrice: 198000,
      pnl: 650000,
      date: "2025-01-18",
    },
    {
      id: "t3",
      symbol: "NAVER",
      side: "BUY",
      qty: 30,
      entryPrice: 195000,
      exitPrice: 212000,
      pnl: 510000,
      date: "2025-01-22",
    },
  ],
  topLosses: [
    {
      id: "t4",
      symbol: "카카오",
      side: "BUY",
      qty: 80,
      entryPrice: 52000,
      exitPrice: 48500,
      pnl: -280000,
      date: "2025-01-10",
    },
    {
      id: "t5",
      symbol: "LG에너지솔루션",
      side: "BUY",
      qty: 10,
      entryPrice: 385000,
      exitPrice: 365000,
      pnl: -200000,
      date: "2025-01-25",
    },
    {
      id: "t6",
      symbol: "셀트리온",
      side: "SELL",
      qty: 40,
      entryPrice: 175000,
      exitPrice: 182000,
      pnl: -280000,
      date: "2025-01-28",
    },
  ],
};

export function getAggregatedStats() {
  const verifiedPerformances = mockPerformances.filter((p) => p.verified);
  if (verifiedPerformances.length === 0) {
    return { totalPnl: 0, maxDrawdown: 0, sharpeRatio: 0, winRate: 0 };
  }

  const totalPnl =
    verifiedPerformances.reduce((sum, p) => sum + p.totalPnl, 0) /
    verifiedPerformances.length;
  const maxDrawdown = Math.min(...verifiedPerformances.map((p) => p.maxDrawdown));
  const sharpeRatio =
    verifiedPerformances.reduce((sum, p) => sum + p.sharpeRatio, 0) /
    verifiedPerformances.length;
  const winRate =
    verifiedPerformances.reduce((sum, p) => sum + p.winRate, 0) /
    verifiedPerformances.length;

  return { totalPnl, maxDrawdown, sharpeRatio, winRate };
}
