"use client";

import {
  AlertTriangle,
  BarChart3,
  FileText,
  LineChart,
  MessageCircle,
  ShieldAlert,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClientBillingChart } from "@/components/dashboard/Charts";
import { ValidationPanel } from "@/components/dashboard/ValidationPanel";
import { useDashboard } from "@/context/DashboardContext";
import type { UploadValidation } from "@/types/dashboard";

function useInsights(validation: UploadValidation): string[] {
  const fromSummary = validation.freelance_summary?.insights ?? [];
  const fromField = validation.freelance_insights ?? [];
  return fromField.length > 0 ? fromField : fromSummary;
}

export function FreelanceOverview({
  validation,
  onAskAi,
}: {
  validation: UploadValidation;
  onAskAi?: () => void;
}) {
  const top = validation.freelance_summary?.top_clients ?? [];
  return (
    <div className="space-y-6 animate-fade-in">
      <ValidationPanel validation={validation} onAskAi={onAskAi} />
      {top.length > 0 && (
        <ClientBillingChart
          data={top.map((c) => ({ name: c.client, amount: c.amount }))}
          title="Top clients by lifetime billing"
        />
      )}
    </div>
  );
}

export function FreelanceAnalytics({ validation }: { validation: UploadValidation }) {
  const clients = validation.freelance_summary?.clients ?? [];
  const top = clients.slice(0, 12);
  const total = validation.freelance_summary?.total_lifetime ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader
        icon={BarChart3}
        title="Client analytics"
        description="Lifetime billing distribution from your upload — not month-by-month trends."
      />
      {top.length > 0 ? (
        <>
          <ClientBillingChart
            data={top.map((c) => ({ name: c.client, amount: c.amount }))}
            title="Billing by client"
            description={`${validation.freelance_summary?.client_count ?? top.length} clients · $${total.toLocaleString()} total`}
          />
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Share of lifetime revenue</CardTitle>
              <CardDescription>Percent of total per client in this export</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {clients.slice(0, 15).map((row, i) => (
                <div key={row.client} className="flex items-center gap-3">
                  <span className="w-6 text-xs text-text-secondary">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex justify-between gap-2 text-sm">
                      <span className="truncate font-medium text-text-primary">{row.client}</span>
                      <span className="shrink-0 text-text-secondary">
                        ${row.amount.toLocaleString()} · {row.share_pct}%
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-accent"
                        style={{ width: `${Math.min(row.share_pct, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      ) : (
        <EmptyChartHint />
      )}
    </div>
  );
}

export function FreelanceInsights({
  validation,
  onAskAi,
}: {
  validation: UploadValidation;
  onAskAi?: () => void;
}) {
  const insights = useInsights(validation);

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader
        icon={FileText}
        title="AI insights from your billing file"
        description="Rule-based analysis of client concentration and priorities — ask the assistant to go deeper."
      />
      <div className="grid gap-3">
        {insights.map((text, i) => (
          <Card key={i} className="border-white/10 bg-surface/40">
            <CardContent className="flex gap-3 py-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-xs font-semibold text-accent">
                {i + 1}
              </span>
              <p className="text-sm leading-relaxed text-text-primary">{text}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {onAskAi && (
        <Button onClick={onAskAi} className="gap-2">
          <MessageCircle className="h-4 w-4" />
          Discuss with AI Analyst
        </Button>
      )}
      <MonthlyPlTeaser />
    </div>
  );
}

const SECTION_COPY: Record<
  string,
  { icon: typeof LineChart; title: string; description: string; bullets: string[] }
> = {
  forecast: {
    icon: LineChart,
    title: "Forecast",
    description: "Project revenue, profit, or expenses forward using your monthly history.",
    bullets: [
      "Needs a CSV with one row per month and a date column.",
      "Export monthly earnings from Upwork or combine invoices into monthly totals.",
      "Use the monthly P&L template under Data when ready.",
    ],
  },
  anomalies: {
    icon: ShieldAlert,
    title: "Anomalies",
    description: "Flags unusual spikes or drops in revenue, expenses, or margin.",
    bullets: [
      "Compares each month to recent patterns in your P&L file.",
      "Lifetime client totals cannot trigger month-level anomaly rules.",
      "Upload dated monthly data to enable this view.",
    ],
  },
  planning: {
    icon: SlidersHorizontal,
    title: "Planning",
    description: "Budget variance, scenarios, benchmarks, and period comparisons.",
    bullets: [
      "Requires monthly actuals plus optional budget columns.",
      "Your Upwork file is great for client mix — use Analytics and AI Insights for that.",
      "Add a monthly file to unlock budget vs actual and what-if scenarios.",
    ],
  },
};

export function FreelanceMonthlyRequired({ section }: { section: string }) {
  const meta = SECTION_COPY[section] ?? SECTION_COPY.forecast;
  const Icon = meta.icon;

  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in pt-4">
      <Card className="border-amber-500/25 bg-gradient-to-br from-amber-500/5 to-card">
        <CardContent className="p-8">
          <div className="flex gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-500/15 ring-1 ring-amber-500/25">
              <Icon className="h-6 w-6 text-amber-400" />
            </div>
            <div>
              <Badge variant="warning" className="mb-2">
                Needs monthly P&L
              </Badge>
              <h2 className="text-xl font-semibold text-text-primary">{meta.title}</h2>
              <p className="mt-2 text-sm text-text-secondary">{meta.description}</p>
            </div>
          </div>
          <ul className="mt-6 space-y-2">
            {meta.bullets.map((b) => (
              <li key={b} className="flex gap-2 text-sm text-text-primary">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                {b}
              </li>
            ))}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="/samples/template_monthly_pl.csv" download>
              <Button variant="secondary" className="gap-2">
                <Upload className="h-4 w-4" />
                Monthly template
              </Button>
            </a>
          </div>
        </CardContent>
      </Card>
      <FreelanceQuickLinks section={section} />
    </div>
  );
}

function FreelanceQuickLinks({ section }: { section: string }) {
  const { setActiveSection } = useDashboard();
  const links =
    section === "forecast" || section === "planning"
      ? [
          { id: "analytics", label: "View client analytics" },
          { id: "insights", label: "Read billing insights" },
        ]
      : [
          { id: "overview", label: "Back to overview" },
          { id: "insights", label: "Billing insights" },
        ];

  return (
    <p className="text-center text-sm text-text-secondary">
      Available now:{" "}
      {links.map((l, i) => (
        <span key={l.id}>
          {i > 0 && " · "}
          <button
            type="button"
            className="text-accent hover:underline"
            onClick={() => setActiveSection(l.id)}
          >
            {l.label}
          </button>
        </span>
      ))}
    </p>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof BarChart3;
  title: string;
  description: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-accent" />
        <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
      </div>
      <p className="mt-1 text-sm text-text-secondary">{description}</p>
    </div>
  );
}

function EmptyChartHint() {
  return (
    <Card className="border-white/10">
      <CardContent className="py-8 text-center text-sm text-text-secondary">
        No client amounts parsed from this file.
      </CardContent>
    </Card>
  );
}

function MonthlyPlTeaser() {
  return (
    <Card className="border-white/10 bg-surface/30">
      <CardContent className="py-4 text-sm text-text-secondary">
        For executive PDF reports and metric-backed narratives, upload a{" "}
        <span className="text-text-primary">monthly P&L</span> file. Your client list stays
        useful here and in chat.
      </CardContent>
    </Card>
  );
}
