"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MonthlyPoint } from "@/types/dashboard";

const tooltipStyle = {
  backgroundColor: "#1F2937",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: "12px",
  color: "#E5E7EB",
};

export function RevenueChart({ data }: { data: MonthlyPoint[] }) {
  return (
    <ChartCard title="Revenue" description="Monthly revenue performance">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="revenue" fill="#3B82F6" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function ProfitChart({ data }: { data: MonthlyPoint[] }) {
  return (
    <ChartCard title="Profitability" description="Gross and net profit trends">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Line type="monotone" dataKey="gross_profit" stroke="#8B5CF6" strokeWidth={2} dot={false} name="Gross profit" />
          <Line type="monotone" dataKey="net_profit" stroke="#10B981" strokeWidth={2} dot={false} name="Net profit" />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function ExpenseChart({
  data,
  categories,
}: {
  data: MonthlyPoint[];
  categories: { category: string; amount: number }[];
}) {
  const catData = categories.length
    ? categories.map((c) => ({ name: c.category, amount: c.amount }))
    : data.map((d) => ({ name: d.month, amount: d.opex }));

  return (
    <ChartCard title="Operating expenses" description="Top categories or monthly opex">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={catData} layout={categories.length ? "vertical" : "horizontal"}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          {categories.length ? (
            <>
              <XAxis type="number" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
              <YAxis type="category" dataKey="name" width={100} tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
            </>
          ) : (
            <>
              <XAxis dataKey="name" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
              <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
            </>
          )}
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="amount" fill="#F59E0B" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function ForecastChart({
  history,
  forecast,
}: {
  history: { month: string; value: number }[];
  forecast: { month: string; value: number; lower: number; upper: number }[];
}) {
  const combined = [
    ...history.map((h) => ({ month: h.month, actual: h.value, forecast: null as number | null })),
    ...forecast.map((f) => ({ month: f.month, actual: null as number | null, forecast: f.value })),
  ];

  return (
    <ChartCard title="Forecast" description="Prophet projection with confidence band">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={combined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
          <YAxis tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Area type="monotone" dataKey="actual" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.2} />
          <Area type="monotone" dataKey="forecast" stroke="#10B981" fill="#10B981" fillOpacity={0.15} strokeDasharray="4 4" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function ClientBillingChart({
  data,
  title = "Client billing",
  description,
}: {
  data: { name: string; amount: number }[];
  title?: string;
  description?: string;
}) {
  const chartData = data.map((d) => ({
    client: d.name.length > 18 ? `${d.name.slice(0, 16)}…` : d.name,
    fullName: d.name,
    amount: d.amount,
  }));

  return (
    <ChartCard title={title} description={description}>
      <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 36)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#9CA3AF", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="client"
            width={120}
            tick={{ fill: "#9CA3AF", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value: number) => [`$${value.toLocaleString()}`, "Billed"]}
            labelFormatter={(_, payload) =>
              payload?.[0]?.payload?.fullName ?? ""
            }
          />
          <Bar dataKey="amount" fill="#F59E0B" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
