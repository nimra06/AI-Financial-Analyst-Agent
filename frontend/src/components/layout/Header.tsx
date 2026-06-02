"use client";

import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { UserMenu, WorkspaceSwitcher } from "@/components/layout/WorkspaceSwitcher";
import { AlertsDropdown } from "@/components/layout/AlertsDropdown";
import { useDashboard } from "@/context/DashboardContext";

export function Header() {
  const { dashboard, uploadValidation } = useDashboard();
  const hasFreelance = Boolean(uploadValidation?.freelance_summary);

  return (
    <header className="relative z-50 flex shrink-0 flex-col gap-2 overflow-visible border-b border-white/[0.06] bg-background/60 px-6 py-3 backdrop-blur-md lg:px-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="min-w-0 truncate text-lg font-semibold leading-tight text-text-primary">
          Financial Command Center
        </h1>
        <div className="flex shrink-0 items-center gap-3">
        <div className="hidden items-center gap-2 rounded-xl border border-white/10 bg-card/50 px-3 py-2 md:flex">
          <Search className="h-4 w-4 text-text-secondary" />
          <span className="text-sm text-text-secondary">Search metrics…</span>
        </div>
        <AlertsDropdown />
        <Badge
          variant={dashboard ? "success" : hasFreelance ? "warning" : "muted"}
        >
          {dashboard ? "Live" : hasFreelance ? "Billing insights" : "No data"}
        </Badge>
        <UserMenu />
        </div>
      </div>
      <div className="min-w-0">
        <WorkspaceSwitcher />
      </div>
    </header>
  );
}
