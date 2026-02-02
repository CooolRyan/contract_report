"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface EquityChartProps {
  data: { date: string; value: number }[];
}

export function EquityChart({ data }: EquityChartProps) {
  const minValue = Math.min(...data.map((d) => d.value));
  const maxValue = Math.max(...data.map((d) => d.value));
  const isPositive = data.length > 0 && data[data.length - 1].value >= data[0].value;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">자산 곡선</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={isPositive ? "oklch(0.65 0.18 145)" : "oklch(0.55 0.2 25)"}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor={isPositive ? "oklch(0.65 0.18 145)" : "oklch(0.55 0.2 25)"}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "oklch(0.6 0 0)", fontSize: 12 }}
                tickFormatter={(value) =>
                  new Date(value).toLocaleDateString("ko-KR", {
                    month: "short",
                    day: "numeric",
                  })
                }
              />
              <YAxis
                domain={[minValue * 0.98, maxValue * 1.02]}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "oklch(0.6 0 0)", fontSize: 12 }}
                tickFormatter={(value) => `${value.toLocaleString()}`}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "oklch(0.14 0 0)",
                  border: "1px solid oklch(0.25 0 0)",
                  borderRadius: "8px",
                  color: "oklch(0.95 0 0)",
                }}
                labelFormatter={(label) =>
                  new Date(label).toLocaleDateString("ko-KR", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                }
                formatter={(value: number) => [
                  `${value.toLocaleString()}원`,
                  "자산",
                ]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={isPositive ? "oklch(0.65 0.18 145)" : "oklch(0.55 0.2 25)"}
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorValue)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
