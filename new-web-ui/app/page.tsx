"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/dashboard/header";
import { Sidebar } from "@/components/dashboard/sidebar";
import { MobileNav } from "@/components/dashboard/mobile-nav";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { PerformanceTable } from "@/components/dashboard/performance-table";
import { EquityChart } from "@/components/dashboard/equity-chart";
import { HashVerification } from "@/components/dashboard/hash-verification";
import { PerformanceDetailView } from "@/components/dashboard/performance-detail";
import type { TabType } from "@/lib/types";
import type { PerformanceSummary, PerformanceDetail } from "@/lib/types";
import type { Trade } from "@/lib/types";
import {
  fetchCommits,
  fetchPerformanceSummary,
  fetchTrades,
  commitToPerformanceSummary,
  equityCurveFromSummary,
  buildTopWinsLosses,
} from "@/lib/api";

function getAggregatedStatsFromPerformances(
  performances: PerformanceSummary[]
): { totalPnl: number; maxDrawdown: number; sharpeRatio: number; winRate: number } {
  const verified = performances.filter((p) => p.verified);
  if (verified.length === 0) {
    return { totalPnl: 0, maxDrawdown: 0, sharpeRatio: 0, winRate: 0 };
  }
  const totalPnl =
    verified.reduce((sum, p) => sum + p.totalPnl, 0) / verified.length;
  const maxDrawdown = Math.min(...verified.map((p) => p.maxDrawdown));
  const sharpeRatio =
    verified.reduce((sum, p) => sum + p.sharpeRatio, 0) / verified.length;
  const winRate =
    verified.reduce((sum, p) => sum + p.winRate, 0) / verified.length;
  return { totalPnl, maxDrawdown, sharpeRatio, winRate };
}

function DashboardContent() {
  const [activeTab, setActiveTab] = useState<TabType>("dashboard");
  const [selectedPerformanceId, setSelectedPerformanceId] = useState<
    string | null
  >(null);

  const { data: commits = [], isLoading: commitsLoading } = useQuery({
    queryKey: ["commits"],
    queryFn: () => fetchCommits(undefined, 50),
  });

  const performances = useMemo(
    () => commits.map(commitToPerformanceSummary),
    [commits]
  );

  const stats = useMemo(
    () => getAggregatedStatsFromPerformances(performances),
    [performances]
  );

  const firstCommit = commits[0];
  const { data: firstSummary } = useQuery({
    queryKey: [
      "summary",
      firstCommit?.trader,
      firstCommit?.periodStart,
      firstCommit?.periodEnd,
    ],
    queryFn: () =>
      fetchPerformanceSummary(
        firstCommit!.trader,
        firstCommit!.periodStart,
        firstCommit!.periodEnd
      ),
    enabled: !!firstCommit?.trader && !!firstCommit?.periodStart && !!firstCommit?.periodEnd,
  });

  const equityChartData = useMemo(() => {
    if (!firstSummary?.summary?.period_start || !firstSummary?.summary?.equity_curve_sampled?.length)
      return [];
    return equityCurveFromSummary(
      firstSummary.summary.period_start,
      firstSummary.summary.equity_curve_sampled
    );
  }, [firstSummary]);

  const handleViewDetail = (id: string) => {
    setSelectedPerformanceId(id);
    setActiveTab("detail");
  };

  const handleBackFromDetail = () => {
    setSelectedPerformanceId(null);
    setActiveTab("dashboard");
  };

  const selectedPerformance = selectedPerformanceId
    ? performances.find((p) => p.id === selectedPerformanceId)
    : null;

  const startParam = selectedPerformance
    ? `${selectedPerformance.periodStart}T00:00:00`
    : "";
  const endParam = selectedPerformance
    ? `${selectedPerformance.periodEnd}T23:59:59`
    : "";

  const { data: detailSummary, isLoading: detailSummaryLoading } = useQuery({
    queryKey: ["detailSummary", selectedPerformance?.trader, startParam, endParam],
    queryFn: () =>
      fetchPerformanceSummary(
        selectedPerformance!.trader,
        startParam,
        endParam
      ),
    enabled: !!selectedPerformance?.trader && !!startParam && !!endParam,
  });

  const { data: detailTrades = [], isLoading: detailTradesLoading } = useQuery({
    queryKey: ["detailTrades", selectedPerformance?.trader, startParam, endParam],
    queryFn: () =>
      fetchTrades(selectedPerformance!.trader, startParam, endParam),
    enabled: !!selectedPerformance?.trader && !!startParam && !!endParam,
  });

  const detailPerformance: PerformanceDetail | null = useMemo(() => {
    if (!selectedPerformance || !detailSummary?.summary) return null;
    const equityCurve =
      detailSummary.summary.equity_curve_sampled?.length &&
      detailSummary.summary.period_start
        ? equityCurveFromSummary(
            detailSummary.summary.period_start,
            detailSummary.summary.equity_curve_sampled
          )
        : [];
    const { topWins, topLosses } = buildTopWinsLosses(detailTrades, 5);
    return {
      ...selectedPerformance,
      equityCurve,
      dailyReturns: [],
      monthlyReturns: [],
      topWins,
      topLosses,
    };
  }, [selectedPerformance, detailSummary, detailTrades]);

  const detailLoading = detailSummaryLoading || detailTradesLoading;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />

      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="flex-1 overflow-auto pb-20 lg:pb-0">
          <div className="container max-w-7xl p-4 md:p-6 lg:p-8">
            {activeTab === "dashboard" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold">대시보드</h2>
                  <p className="text-muted-foreground">
                    온체인에 기록된 트레이딩 성과를 확인하세요
                  </p>
                </div>

                <StatsCards
                  totalPnl={stats.totalPnl}
                  maxDrawdown={stats.maxDrawdown}
                  sharpeRatio={stats.sharpeRatio}
                  winRate={stats.winRate}
                />

                <div className="grid gap-6 xl:grid-cols-2">
                  {commitsLoading ? (
                    <div className="flex h-[300px] items-center justify-center rounded-lg border border-border bg-card text-muted-foreground">
                      로딩 중...
                    </div>
                  ) : equityChartData.length > 0 ? (
                    <EquityChart data={equityChartData} />
                  ) : (
                    <div className="flex h-[300px] items-center justify-center rounded-lg border border-border bg-card text-muted-foreground">
                      커밋 기록이 있으면 자산 곡선이 표시됩니다
                    </div>
                  )}

                  <PerformanceTable
                    performances={performances}
                    onViewDetail={handleViewDetail}
                  />
                </div>
              </div>
            )}

            {activeTab === "verify" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold">해시 검증</h2>
                  <p className="text-muted-foreground">
                    성과 데이터의 무결성을 검증하세요
                  </p>
                </div>

                <div className="mx-auto max-w-2xl">
                  <HashVerification />
                </div>
              </div>
            )}

            {activeTab === "detail" && (
              detailLoading ? (
                <div className="flex min-h-[400px] items-center justify-center text-muted-foreground">
                  로딩 중...
                </div>
              ) : detailPerformance ? (
                <PerformanceDetailView
                  performance={detailPerformance}
                  onBack={handleBackFromDetail}
                />
              ) : selectedPerformance ? (
                <div className="flex min-h-[400px] items-center justify-center text-muted-foreground">
                  상세 데이터를 불러올 수 없습니다.
                </div>
              ) : null
            )}
          </div>
        </main>
      </div>

      <MobileNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
}

export default function Page() {
  return <DashboardContent />;
}
