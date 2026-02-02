"use client";

import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity, Target } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsCardsProps {
  totalPnl: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
}

export function StatsCards({
  totalPnl,
  maxDrawdown,
  sharpeRatio,
  winRate,
}: StatsCardsProps) {
  const stats = [
    {
      label: "총 수익률",
      value: `${totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}%`,
      icon: totalPnl >= 0 ? TrendingUp : TrendingDown,
      positive: totalPnl >= 0,
    },
    {
      label: "최대 낙폭 (MDD)",
      value: `${maxDrawdown.toFixed(2)}%`,
      icon: TrendingDown,
      positive: false,
    },
    {
      label: "샤프 비율",
      value: sharpeRatio.toFixed(2),
      icon: Activity,
      positive: sharpeRatio > 1,
    },
    {
      label: "승률",
      value: `${winRate.toFixed(1)}%`,
      icon: Target,
      positive: winRate >= 50,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="bg-card">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p
                  className={cn(
                    "mt-1 text-2xl font-bold",
                    stat.positive ? "text-success" : "text-destructive"
                  )}
                >
                  {stat.value}
                </p>
              </div>
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  stat.positive
                    ? "bg-success/10 text-success"
                    : "bg-destructive/10 text-destructive"
                )}
              >
                <stat.icon className="h-5 w-5" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
