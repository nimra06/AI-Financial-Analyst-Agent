"use client";

import { useEffect } from "react";
import { Database, Download, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileUpload } from "@/components/dashboard/FileUpload";
import { ValidationPanel } from "@/components/dashboard/ValidationPanel";
import { AuditLogPanel, RetentionNotice } from "@/components/dashboard/AuditLogPanel";
import { AdminPanel } from "@/components/dashboard/AdminPanel";
import { useDashboard } from "@/context/DashboardContext";

export function DataHub() {
  const {
    sessions,
    loadSession,
    refreshSessions,
    dashboard,
    uploadValidation,
    clearUploadValidation,
  } = useDashboard();

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  return (
    <div className="space-y-8 animate-fade-in">
      <RetentionNotice />
      {dashboard && (
        <Card className="border-accent/25 bg-accent/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/20 ring-1 ring-accent/30">
                <Database className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Active workspace
                </p>
                <p className="font-semibold text-text-primary">{dashboard.source_file}</p>
                <p className="text-xs text-text-secondary">
                  {dashboard.period_count} periods · latest {dashboard.kpis.latest_month}
                </p>
              </div>
            </div>
            <Badge variant="success">Live</Badge>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Import financial data</CardTitle>
            <p className="mt-1 text-sm text-text-secondary">
              CSV or Excel · validated before analysis
            </p>
          </div>
          <a
            href="/samples/template_monthly_pl.csv"
            download
            className="flex items-center gap-1.5 text-sm text-accent hover:underline"
          >
            <Download className="h-4 w-4" />
            Template
          </a>
        </CardHeader>
        <CardContent className="space-y-4">
          {uploadValidation && (
            <ValidationPanel
              validation={uploadValidation}
              onDismiss={clearUploadValidation}
            />
          )}
          <FileUpload />
          <p className="text-xs text-text-secondary">
            Required columns: <code className="text-accent">date</code>,{" "}
            <code className="text-accent">revenue</code> (or{" "}
            <code className="text-accent">category</code> +{" "}
            <code className="text-accent">amount</code>)
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Datasets</CardTitle>
          <Badge variant="muted">{sessions.length} saved</Badge>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {sessions.length === 0 ? (
            <p className="py-8 text-center text-sm text-text-secondary">
              No datasets yet. Import a file above to create your first workspace.
            </p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-text-secondary">
                  <th className="pb-3 pr-4 font-medium">File</th>
                  <th className="pb-3 pr-4 font-medium">Periods</th>
                  <th className="pb-3 pr-4 font-medium">Latest</th>
                  <th className="pb-3 pr-4 font-medium">Uploaded</th>
                  <th className="pb-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr
                    key={s.session_id}
                    className={`border-b border-white/5 ${
                      dashboard?.session_id === s.session_id ? "bg-accent/5" : ""
                    }`}
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-accent" />
                        <span className="text-text-primary">{s.source_file}</span>
                        {dashboard?.session_id === s.session_id && (
                          <Badge variant="success" className="text-[10px]">
                            Active
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-text-secondary">{s.period_count}</td>
                    <td className="py-3 pr-4 text-text-secondary">{s.latest_month}</td>
                    <td className="py-3 pr-4 text-text-secondary">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <button
                        type="button"
                        onClick={() => loadSession(s.session_id)}
                        className="text-sm font-medium text-accent hover:underline"
                      >
                        {dashboard?.session_id === s.session_id ? "Current" : "Open"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <AdminPanel />
      <AuditLogPanel />
    </div>
  );
}
