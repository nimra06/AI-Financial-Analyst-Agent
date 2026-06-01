"use client";

import {
  BarChart3,
  FileText,
  LayoutDashboard,
  LineChart,
  ShieldAlert,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDashboard } from "@/context/DashboardContext";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "insights", label: "AI Insights", icon: FileText },
  { id: "forecast", label: "Forecast", icon: LineChart },
  { id: "anomalies", label: "Anomalies", icon: ShieldAlert },
  { id: "planning", label: "Planning", icon: SlidersHorizontal },
  { id: "data", label: "Data", icon: Upload },
];

export function Sidebar() {
  const { activeSection, setActiveSection, dashboard, uploadValidation } = useDashboard();
  const hasFreelance = Boolean(
    uploadValidation?.freelance_summary &&
      uploadValidation.detected_format === "freelance_client_billing"
  );
  const canUseSections = Boolean(dashboard || hasFreelance);

  return (
    <aside className="flex h-full w-64 flex-col border-r border-white/[0.06] bg-surface/80 backdrop-blur-xl">
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/20 ring-1 ring-accent/30">
          <BarChart3 className="h-5 w-5 text-accent" />
        </div>
        <div>
          <p className="text-sm font-semibold text-text-primary">FinAnalyst AI</p>
          <p className="text-xs text-text-secondary">Enterprise</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            disabled={!canUseSections && id !== "overview" && id !== "data"}
            onClick={() => setActiveSection(id)}
            className={cn(
              "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
              activeSection === id
                ? "bg-accent/15 text-text-primary ring-1 ring-accent/25"
                : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
              !canUseSections && id !== "overview" && id !== "data" && "opacity-40"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </button>
        ))}
      </nav>

      <div className="border-t border-white/[0.06] p-4">
        <p className="text-xs text-text-secondary">
          Demo only · Not financial advice
        </p>
      </div>
    </aside>
  );
}
