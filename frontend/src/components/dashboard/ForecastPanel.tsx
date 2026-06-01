"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ForecastChart } from "@/components/dashboard/Charts";
import { useDashboard } from "@/context/DashboardContext";
import { formatCurrency } from "@/lib/utils";

export function ForecastPanel() {
  const { forecast, runForecast, loading, dashboard } = useDashboard();
  const [metric, setMetric] = useState<"revenue" | "opex">("revenue");
  const [horizon, setHorizon] = useState<3 | 12>(3);

  if (!dashboard) return null;

  const history =
    forecast?.history.map((h) => ({ month: h.month, value: h.value })) ?? [];
  const fc = forecast?.forecast ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="text-xs text-text-secondary">Metric</label>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as "revenue" | "opex")}
            className="mt-1 block rounded-xl border border-white/10 bg-card px-3 py-2 text-sm"
          >
            <option value="revenue">Revenue</option>
            <option value="opex">Operating expenses</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-text-secondary">Horizon</label>
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value) as 3 | 12)}
            className="mt-1 block rounded-xl border border-white/10 bg-card px-3 py-2 text-sm"
          >
            <option value={3}>1 quarter (3 mo)</option>
            <option value={12}>1 year (12 mo)</option>
          </select>
        </div>
        <Button onClick={() => runForecast(metric, horizon)} disabled={loading}>
          {horizon >= 12 ? "Run forecast (background)" : "Run forecast"}
        </Button>
      </div>

      {forecast && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Metric label="Forecast total" value={formatCurrency(Number(forecast.summary.forecast_total))} />
            <Metric label="Avg monthly" value={formatCurrency(Number(forecast.summary.forecast_avg_monthly))} />
            <Metric label="End of horizon" value={formatCurrency(Number(forecast.summary.forecast_end_value))} />
          </div>
          <ForecastChart history={history} forecast={fc} />
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-card rounded-2xl p-4">
      <p className="text-xs text-text-secondary">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}
