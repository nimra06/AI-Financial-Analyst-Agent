"use client";

import { useEffect, useState } from "react";
import { KpiCards } from "@/components/dashboard/KpiCards";
import {
  ExpenseChart,
  ProfitChart,
  RevenueChart,
} from "@/components/dashboard/Charts";
import { InsightsPanel } from "@/components/dashboard/InsightsPanel";
import { ForecastPanel } from "@/components/dashboard/ForecastPanel";
import { AnomaliesPanel } from "@/components/dashboard/AnomaliesPanel";
import { PlanningPanel } from "@/components/dashboard/PlanningPanel";
import {
  FreelanceAnalytics,
  FreelanceInsights,
  FreelanceMonthlyRequired,
  FreelanceOverview,
} from "@/components/dashboard/FreelanceViews";
import { DataHub } from "@/components/dashboard/DataHub";
import { WhyPanel } from "@/components/dashboard/WhyPanel";
import { useDashboard } from "@/context/DashboardContext";
import { fetchWhyPanel } from "@/lib/api";
import type { WhyInsight } from "@/types/dashboard";

export function DashboardView() {
  const {
    dashboard,
    activeSection,
    error,
    workspaceLoading,
    uploadValidation,
    setChatOpen,
  } = useDashboard();
  const [why, setWhy] = useState<WhyInsight[]>([]);

  const hasFreelance = Boolean(
    uploadValidation?.freelance_summary &&
      uploadValidation.detected_format === "freelance_client_billing"
  );

  const openChat = () => setChatOpen(true);

  useEffect(() => {
    if (dashboard) {
      fetchWhyPanel(dashboard).then(setWhy).catch(() => setWhy([]));
    }
  }, [dashboard]);

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        {error}
      </div>
    );
  }

  if (activeSection === "data") {
    return <DataHub />;
  }

  if (!dashboard && hasFreelance && uploadValidation) {
    switch (activeSection) {
      case "overview":
        return <FreelanceOverview validation={uploadValidation} onAskAi={openChat} />;
      case "analytics":
        return <FreelanceAnalytics validation={uploadValidation} />;
      case "insights":
        return <FreelanceInsights validation={uploadValidation} onAskAi={openChat} />;
      case "forecast":
        return <FreelanceMonthlyRequired section="forecast" />;
      case "anomalies":
        return <FreelanceMonthlyRequired section="anomalies" />;
      case "planning":
        return <FreelanceMonthlyRequired section="planning" />;
      default:
        return <FreelanceOverview validation={uploadValidation} onAskAi={openChat} />;
    }
  }

  if (!dashboard) {
    if (workspaceLoading) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 py-24">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          <p className="text-sm text-text-secondary">Loading your workspace…</p>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-2xl space-y-6 pt-12">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-text-primary">No dataset loaded</h2>
          <p className="mt-2 text-sm text-text-secondary">
            Import a financial file in Data to start analysis.
          </p>
        </div>
        <DataHub />
      </div>
    );
  }

  switch (activeSection) {
    case "overview":
      return (
        <div className="space-y-8 animate-fade-in">
          <KpiCards kpis={dashboard.kpis} />
          <div className="grid gap-6 xl:grid-cols-2">
            <RevenueChart data={dashboard.chart_series} />
            <ProfitChart data={dashboard.chart_series} />
          </div>
          {why.length > 0 && <WhyPanel insights={why.slice(0, 6)} />}
        </div>
      );
    case "analytics":
      return (
        <div className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-2">
            <RevenueChart data={dashboard.chart_series} />
            <ProfitChart data={dashboard.chart_series} />
            <ExpenseChart
              data={dashboard.chart_series}
              categories={dashboard.top_expense_categories}
            />
          </div>
        </div>
      );
    case "insights":
      return <InsightsPanel />;
    case "forecast":
      return <ForecastPanel />;
    case "anomalies":
      return <AnomaliesPanel dashboard={dashboard} />;
    case "planning":
      return <PlanningPanel />;
    default:
      return null;
  }
}
