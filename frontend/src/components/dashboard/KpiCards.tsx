"use client";

import { DollarSign, Percent, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency, formatPct } from "@/lib/utils";
import type { Kpis } from "@/types/dashboard";

interface Props {
  kpis: Kpis;
}

export function KpiCards({ kpis }: Props) {
  const items = [
    {
      label: "Latest revenue",
      value: formatCurrency(kpis.latest_revenue),
      sub: formatPct(kpis.mom_revenue_growth_pct) + " MoM",
      up: (kpis.mom_revenue_growth_pct ?? 0) >= 0,
      icon: DollarSign,
    },
    {
      label: "Net profit",
      value: formatCurrency(kpis.latest_net_profit),
      sub: formatPct(kpis.mom_profit_growth_pct) + " MoM",
      up: (kpis.mom_profit_growth_pct ?? 0) >= 0,
      icon: TrendingUp,
    },
    {
      label: "Gross margin",
      value: `${kpis.latest_gross_margin_pct.toFixed(1)}%`,
      sub: `Opex ratio ${kpis.latest_opex_ratio_pct.toFixed(1)}%`,
      up: kpis.latest_gross_margin_pct >= 30,
      icon: Percent,
    },
    {
      label: "3-mo avg revenue",
      value: formatCurrency(kpis.avg_revenue_3m),
      sub: `Best: ${kpis.best_month_by_revenue}`,
      up: true,
      icon: TrendingDown,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card
          key={item.label}
          className="animate-slide-up transition duration-200 hover:border-white/10 hover:shadow-glow"
        >
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  {item.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-text-primary">
                  {item.value}
                </p>
                <p
                  className={`mt-1 text-xs ${
                    item.up ? "text-success" : "text-warning"
                  }`}
                >
                  {item.sub}
                </p>
              </div>
              <div className="rounded-xl bg-white/5 p-2.5">
                <item.icon className="h-4 w-4 text-accent" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
