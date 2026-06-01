"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeftRight,
  BarChart3,
  Calendar,
  GitCompare,
  SlidersHorizontal,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useDashboard } from "@/context/DashboardContext";
import { useAuth } from "@/context/AuthContext";
import { canWrite } from "@/lib/permissions";
import {
  compareSessions,
  createScheduledReport,
  fetchIndustries,
  listScheduledReports,
  pollJob,
  runScenario,
  runScheduledReport,
} from "@/lib/api";
import type {
  CompareResult,
  ScenarioResult,
  ScheduledReport,
} from "@/types/dashboard";

type Tab = "budget" | "benchmarks" | "compare" | "scenarios" | "schedules";

export function PlanningPanel() {
  const { dashboard, sessions } = useDashboard();
  const { user } = useAuth();
  const writeAccess = canWrite(user);
  const [tab, setTab] = useState<Tab>("budget");
  const [compareB, setCompareB] = useState("");
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [revDelta, setRevDelta] = useState(0);
  const [opexDelta, setOpexDelta] = useState(-10);
  const [industries, setIndustries] = useState<{ id: string; label: string }[]>([]);
  const [schedules, setSchedules] = useState<ScheduledReport[]>([]);
  const [scheduleEmail, setScheduleEmail] = useState(user?.email ?? "");
  const [scheduleStatus, setScheduleStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchIndustries().then(setIndustries).catch(() => {});
  }, []);

  useEffect(() => {
    if (dashboard?.session_id) {
      listScheduledReports(dashboard.session_id).then(setSchedules).catch(() => setSchedules([]));
    }
  }, [dashboard?.session_id]);

  if (!dashboard) return null;

  const tabs: { id: Tab; label: string; icon: typeof Target }[] = [
    { id: "budget", label: "Budget", icon: Target },
    { id: "benchmarks", label: "Benchmarks", icon: BarChart3 },
    { id: "compare", label: "Compare", icon: GitCompare },
    { id: "scenarios", label: "Scenarios", icon: SlidersHorizontal },
    { id: "schedules", label: "Reports", icon: Calendar },
  ];

  const runCompare = async () => {
    if (!compareB) return;
    const res = await compareSessions(dashboard.session_id, compareB);
    setCompareResult(res);
  };

  const runScen = async () => {
    const res = await runScenario(dashboard.monthly_records, {
      revenue_delta_pct: revDelta,
      opex_delta_pct: opexDelta,
    });
    setScenario(res);
  };

  const runScheduleNow = async (reportId: number) => {
    setScheduleStatus("Queued…");
    try {
      const { job_id } = await runScheduledReport(reportId);
      await pollJob(job_id, () => true, 1500, 60);
      setScheduleStatus("Report generated in background.");
      const list = await listScheduledReports(dashboard.session_id);
      setSchedules(list);
    } catch {
      setScheduleStatus("Job failed or timed out — ensure worker is running.");
    }
  };

  const addSchedule = async () => {
    if (!scheduleEmail.trim()) return;
    await createScheduledReport({
      session_id: dashboard.session_id,
      label: `Weekly · ${dashboard.source_file}`,
      cadence: "weekly",
      format: "pdf",
      recipients: [scheduleEmail.trim()],
    });
    const list = await listScheduledReports(dashboard.session_id);
    setSchedules(list);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">Planning & intelligence</h2>
        <p className="text-sm text-text-secondary">
          Budget variance, benchmarks, multi-dataset compare, what-if scenarios, scheduled exports
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition ${
              tab === id
                ? "bg-accent/15 text-text-primary ring-1 ring-accent/25"
                : "text-text-secondary hover:bg-white/5"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "budget" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Budget vs actual</CardTitle>
          </CardHeader>
          <CardContent>
            {dashboard.budget_variance?.available ? (
              <div className="space-y-4">
                <p className="text-xs text-text-secondary">
                  Latest period: {dashboard.budget_variance.latest_month}
                </p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-text-secondary">
                      <th className="pb-2">Metric</th>
                      <th className="pb-2">Actual</th>
                      <th className="pb-2">Budget</th>
                      <th className="pb-2">Variance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.budget_variance.lines?.map((line) => (
                      <tr key={line.metric} className="border-b border-white/5">
                        <td className="py-2 capitalize">{line.metric}</td>
                        <td className="py-2">${line.actual.toLocaleString()}</td>
                        <td className="py-2">${line.budget.toLocaleString()}</td>
                        <td
                          className={`py-2 ${line.favorable ? "text-success" : "text-warning"}`}
                        >
                          {line.variance_pct != null
                            ? `${line.variance_pct > 0 ? "+" : ""}${line.variance_pct}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-secondary">
                {dashboard.budget_variance?.reason ??
                  "Add budget_revenue and budget_opex columns to your CSV."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "benchmarks" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm">Industry benchmarks</CardTitle>
            <Badge variant="muted">{dashboard.industry ?? "saas"}</Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-text-secondary">
              {dashboard.benchmarks?.disclaimer}
            </p>
            {dashboard.benchmarks?.scores?.map((s) => (
              <div
                key={s.metric}
                className="flex items-center justify-between rounded-xl border border-white/10 bg-surface/50 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-text-primary">{s.metric}</p>
                  <p className="text-xs text-text-secondary">
                    Typical: {s.benchmark_low}–{s.benchmark_high} (mid {s.benchmark_mid})
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold">{s.value}</p>
                  <Badge
                    variant={
                      s.status === "in_range"
                        ? "success"
                        : s.status === "below"
                          ? "warning"
                          : "muted"
                    }
                  >
                    {s.status.replace("_", " ")}
                  </Badge>
                </div>
              </div>
            ))}
            <p className="text-xs text-text-secondary">
              Industries: {industries.map((i) => i.label).join(", ")} — auto-detected from filename
            </p>
          </CardContent>
        </Card>
      )}

      {tab === "compare" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ArrowLeftRight className="h-4 w-4" />
              Compare datasets
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-text-secondary">
              Active: <strong>{dashboard.source_file}</strong>
            </p>
            <select
              value={compareB}
              onChange={(e) => setCompareB(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
            >
              <option value="">Select second dataset…</option>
              {sessions
                .filter((s) => s.session_id !== dashboard.session_id)
                .map((s) => (
                  <option key={s.session_id} value={s.session_id}>
                    {s.source_file} ({s.period_count} periods)
                  </option>
                ))}
            </select>
            <Button onClick={runCompare} disabled={!compareB}>
              Compare
            </Button>
            {compareResult && (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-secondary">
                    <th className="pb-2 text-left">Metric</th>
                    <th className="pb-2 text-left">{compareResult.session_a.source_file}</th>
                    <th className="pb-2 text-left">{compareResult.session_b.source_file}</th>
                    <th className="pb-2 text-left">Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {compareResult.deltas.map((d) => (
                    <tr key={d.metric} className="border-t border-white/5">
                      <td className="py-2">{d.metric}</td>
                      <td className="py-2">{d.session_a}</td>
                      <td className="py-2">{d.session_b}</td>
                      <td className="py-2">{d.delta_pct != null ? `${d.delta_pct}%` : d.delta}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "scenarios" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">What-if scenario</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-xs text-text-secondary">
                Revenue change (%)
                <input
                  type="number"
                  value={revDelta}
                  onChange={(e) => setRevDelta(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
                />
              </label>
              <label className="text-xs text-text-secondary">
                Opex change (%)
                <input
                  type="number"
                  value={opexDelta}
                  onChange={(e) => setOpexDelta(Number(e.target.value))}
                  className="mt-1 w-full rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
                />
              </label>
            </div>
            <Button onClick={runScen} disabled={!writeAccess}>
              Run scenario
            </Button>
            {scenario && (
              <div className="space-y-2 rounded-xl border border-white/10 bg-surface/50 p-4">
                <p className="text-sm font-medium">
                  Latest month impact ({scenario.latest_month})
                </p>
                {scenario.impact.map((row) => (
                  <div key={row.metric} className="flex justify-between text-sm">
                    <span className="capitalize text-text-secondary">{row.metric}</span>
                    <span>
                      ${row.baseline.toLocaleString()} → ${row.projected.toLocaleString()}
                      {row.delta_pct != null && (
                        <span className="ml-2 text-accent">({row.delta_pct}%)</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "schedules" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Scheduled executive reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-text-secondary">
              Background worker generates PDF reports (run{" "}
              <code className="rounded bg-white/5 px-1">python -m worker.runner</code> locally).
            </p>
            {scheduleStatus && (
              <p className="text-xs text-accent">{scheduleStatus}</p>
            )}
            {writeAccess && (
              <div className="flex gap-2">
                <input
                  value={scheduleEmail}
                  onChange={(e) => setScheduleEmail(e.target.value)}
                  placeholder="recipient@company.com"
                  className="flex-1 rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
                />
                <Button onClick={addSchedule}>Schedule weekly</Button>
              </div>
            )}
            {schedules.length === 0 ? (
              <p className="text-sm text-text-secondary">No schedules yet.</p>
            ) : (
              <ul className="space-y-2">
                {schedules.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-3 text-sm"
                  >
                    <div>
                      <p className="font-medium">{s.label}</p>
                      <p className="text-xs text-text-secondary">
                        {s.cadence} · {s.format.toUpperCase()} · {s.recipients.join(", ")}
                      </p>
                    </div>
                    {writeAccess && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => runScheduleNow(s.id)}
                      >
                        Run now
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
