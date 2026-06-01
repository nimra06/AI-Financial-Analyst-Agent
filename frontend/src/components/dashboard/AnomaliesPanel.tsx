"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import type { DashboardData } from "@/types/dashboard";

export function AnomaliesPanel({ dashboard }: { dashboard: DashboardData }) {
  const { flags, summary } = dashboard.anomalies;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap gap-4">
        <Stat label="Flags" value={String(summary.count ?? 0)} />
        <Stat label="High severity" value={String(summary.high_severity ?? 0)} />
        <Stat label="Months flagged" value={String(summary.months_flagged ?? 0)} />
      </div>

      {flags.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-text-secondary">
            No statistical anomalies detected for this dataset.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Detected anomalies</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-text-secondary">
                  <th className="pb-3 pr-4 font-medium">Month</th>
                  <th className="pb-3 pr-4 font-medium">Metric</th>
                  <th className="pb-3 pr-4 font-medium">Value</th>
                  <th className="pb-3 pr-4 font-medium">Method</th>
                  <th className="pb-3 font-medium">Description</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((f, i) => (
                  <tr key={i} className="border-b border-white/5 text-text-primary">
                    <td className="py-3 pr-4">{f.month}</td>
                    <td className="py-3 pr-4">{f.metric}</td>
                    <td className="py-3 pr-4">{formatCurrency(f.value)}</td>
                    <td className="py-3 pr-4">
                      <Badge variant={f.severity === "high" ? "warning" : "muted"}>
                        {f.method}
                      </Badge>
                    </td>
                    <td className="py-3 text-text-secondary">{f.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card className="min-w-[140px]">
      <CardContent className="p-4">
        <p className="text-xs text-text-secondary">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
