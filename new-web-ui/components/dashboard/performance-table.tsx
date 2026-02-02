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
import { ExternalLink, Eye, CheckCircle, Clock } from "lucide-react";
import type { PerformanceSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PerformanceTableProps {
  performances: PerformanceSummary[];
  onViewDetail: (id: string) => void;
}

function formatAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function PerformanceTable({
  performances,
  onViewDetail,
}: PerformanceTableProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">온체인 성과 기록</CardTitle>
        <Button variant="outline" size="sm">
          새로고침
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>트레이더</TableHead>
                <TableHead>기간</TableHead>
                <TableHead className="text-right">수익률</TableHead>
                <TableHead className="text-right">MDD</TableHead>
                <TableHead className="text-right">샤프</TableHead>
                <TableHead>상태</TableHead>
                <TableHead className="text-right">액션</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {performances.map((perf) => (
                <TableRow key={perf.id}>
                  <TableCell className="font-mono text-sm">
                    {formatAddress(perf.trader)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(perf.periodStart)} - {formatDate(perf.periodEnd)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-medium",
                      perf.totalPnl >= 0 ? "text-success" : "text-destructive"
                    )}
                  >
                    {perf.totalPnl >= 0 ? "+" : ""}
                    {perf.totalPnl.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right text-destructive">
                    {perf.maxDrawdown.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">
                    {perf.sharpeRatio.toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={perf.verified ? "default" : "secondary"}
                      className={cn(
                        "gap-1",
                        perf.verified
                          ? "bg-success/10 text-success hover:bg-success/20"
                          : ""
                      )}
                    >
                      {perf.verified ? (
                        <CheckCircle className="h-3 w-3" />
                      ) : (
                        <Clock className="h-3 w-3" />
                      )}
                      {perf.verified ? "검증됨" : "대기중"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onViewDetail(perf.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        asChild
                      >
                        <a
                          href={`https://sepolia.etherscan.io/tx/${perf.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
