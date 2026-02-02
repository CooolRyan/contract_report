"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  ExternalLink,
  Copy,
  TrendingUp,
  TrendingDown,
  Calendar,
  Hash,
  CheckCircle,
} from "lucide-react";
import type { PerformanceDetail, Trade } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EquityChart } from "./equity-chart";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";

interface PerformanceDetailViewProps {
  performance: PerformanceDetail;
  onBack: () => void;
}

function formatAddress(address: string): string {
  return `${address.slice(0, 10)}...${address.slice(-8)}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function TradeTable({ trades, type }: { trades: Trade[]; type: "win" | "loss" }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>종목</TableHead>
          <TableHead>방향</TableHead>
          <TableHead className="text-right">수량</TableHead>
          <TableHead className="text-right">진입가</TableHead>
          <TableHead className="text-right">청산가</TableHead>
          <TableHead className="text-right">손익</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((trade) => (
          <TableRow key={trade.id}>
            <TableCell className="font-medium">{trade.symbol}</TableCell>
            <TableCell>
              <Badge
                variant="outline"
                className={cn(
                  trade.side === "BUY"
                    ? "border-success/50 text-success"
                    : "border-destructive/50 text-destructive"
                )}
              >
                {trade.side === "BUY" ? "매수" : "매도"}
              </Badge>
            </TableCell>
            <TableCell className="text-right">{trade.qty}</TableCell>
            <TableCell className="text-right">
              {trade.entryPrice.toLocaleString()}
            </TableCell>
            <TableCell className="text-right">
              {trade.exitPrice.toLocaleString()}
            </TableCell>
            <TableCell
              className={cn(
                "text-right font-medium",
                type === "win" ? "text-success" : "text-destructive"
              )}
            >
              {trade.pnl >= 0 ? "+" : ""}
              {trade.pnl.toLocaleString()}원
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function PerformanceDetailView({
  performance,
  onBack,
}: PerformanceDetailViewProps) {
  const copyHash = () => {
    navigator.clipboard.writeText(performance.hash);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h2 className="text-xl font-semibold">성과 상세</h2>
            <p className="text-sm text-muted-foreground">
              {formatDate(performance.periodStart)} -{" "}
              {formatDate(performance.periodEnd)}
            </p>
          </div>
        </div>
        <Badge
          variant="default"
          className="gap-1 bg-success/10 text-success hover:bg-success/20"
        >
          <CheckCircle className="h-3 w-3" />
          온체인 검증됨
        </Badge>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  performance.totalPnl >= 0
                    ? "bg-success/10 text-success"
                    : "bg-destructive/10 text-destructive"
                )}
              >
                {performance.totalPnl >= 0 ? (
                  <TrendingUp className="h-5 w-5" />
                ) : (
                  <TrendingDown className="h-5 w-5" />
                )}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">총 수익률</p>
                <p
                  className={cn(
                    "text-xl font-bold",
                    performance.totalPnl >= 0 ? "text-success" : "text-destructive"
                  )}
                >
                  {performance.totalPnl >= 0 ? "+" : ""}
                  {performance.totalPnl.toFixed(2)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
                <TrendingDown className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">최대 낙폭</p>
                <p className="text-xl font-bold text-destructive">
                  {performance.maxDrawdown.toFixed(2)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Calendar className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">거래 횟수</p>
                <p className="text-xl font-bold">{performance.tradeCount}회</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  performance.winRate >= 50
                    ? "bg-success/10 text-success"
                    : "bg-destructive/10 text-destructive"
                )}
              >
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">승률</p>
                <p
                  className={cn(
                    "text-xl font-bold",
                    performance.winRate >= 50 ? "text-success" : "text-destructive"
                  )}
                >
                  {performance.winRate.toFixed(1)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* On-chain Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Hash className="h-5 w-5 text-primary" />
            온체인 정보
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">트레이더 주소</p>
              <code className="block rounded bg-muted px-3 py-2 font-mono text-sm">
                {formatAddress(performance.trader)}
              </code>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">트랜잭션 해시</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded bg-muted px-3 py-2 font-mono text-sm">
                  {performance.txHash}
                </code>
                <Button variant="ghost" size="icon" className="shrink-0" asChild>
                  <a
                    href={`https://sepolia.etherscan.io/tx/${performance.txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </Button>
              </div>
            </div>
            <div className="space-y-1 sm:col-span-2">
              <p className="text-xs text-muted-foreground">성과 해시 (SHA-256)</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded bg-muted px-3 py-2 font-mono text-sm">
                  {performance.hash}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  className="shrink-0"
                  onClick={copyHash}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <EquityChart data={performance.equityCurve} />

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">월별 수익률</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={performance.monthlyReturns}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="month"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "oklch(0.6 0 0)", fontSize: 12 }}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "oklch(0.6 0 0)", fontSize: 12 }}
                    tickFormatter={(value) => `${value}%`}
                    width={50}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "oklch(0.14 0 0)",
                      border: "1px solid oklch(0.25 0 0)",
                      borderRadius: "8px",
                      color: "oklch(0.95 0 0)",
                    }}
                    formatter={(value: number) => [`${value.toFixed(2)}%`, "수익률"]}
                  />
                  <Bar dataKey="return" radius={[4, 4, 0, 0]}>
                    {performance.monthlyReturns.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          entry.return >= 0
                            ? "oklch(0.65 0.18 145)"
                            : "oklch(0.55 0.2 25)"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trade Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">거래 내역</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="wins">
            <TabsList>
              <TabsTrigger value="wins" className="gap-2">
                <TrendingUp className="h-4 w-4 text-success" />
                Top 수익
              </TabsTrigger>
              <TabsTrigger value="losses" className="gap-2">
                <TrendingDown className="h-4 w-4 text-destructive" />
                Top 손실
              </TabsTrigger>
            </TabsList>
            <TabsContent value="wins" className="mt-4">
              <TradeTable trades={performance.topWins} type="win" />
            </TabsContent>
            <TabsContent value="losses" className="mt-4">
              <TradeTable trades={performance.topLosses} type="loss" />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
