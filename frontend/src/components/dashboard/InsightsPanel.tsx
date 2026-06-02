"use client";

import { useState } from "react";
import { Download, FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/context/DashboardContext";
import { useAuth } from "@/context/AuthContext";
import { canWrite } from "@/lib/permissions";
import {
  downloadBase64Pdf,
  downloadText,
  generateExecutiveReport,
} from "@/lib/api";

export function InsightsPanel() {
  const { summary, runSummary, loading, dashboard } = useDashboard();
  const { user } = useAuth();
  const writeAccess = canWrite(user);
  const [exporting, setExporting] = useState(false);
  const [exportWarnings, setExportWarnings] = useState<string[]>([]);

  if (!dashboard) return null;

  const exportReport = async (format: "html" | "markdown" | "pdf") => {
    setExporting(true);
    setExportWarnings([]);
    try {
      const report = await generateExecutiveReport(dashboard, summary);
      setExportWarnings(report.warnings);
      const base = dashboard.source_file.replace(/\.[^.]+$/, "") || "report";
      if (format === "html") {
        downloadText(report.html, `${base}_executive.html`, "text/html");
      } else if (format === "markdown") {
        downloadText(report.markdown, `${base}_executive.md`, "text/markdown");
      } else if (report.pdf_available && report.pdf_base64) {
        downloadBase64Pdf(report.pdf_base64, `${base}_executive.pdf`);
      }
    } catch (e) {
      setExportWarnings([e instanceof Error ? e.message : "Export failed"]);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">AI-generated insights</h2>
          <p className="text-sm text-text-secondary">
            Metric-backed executive narrative — numbers verified against your data
          </p>
        </div>
        <Button onClick={runSummary} disabled={loading || !writeAccess}>
          <Sparkles className="h-4 w-4" />
          Generate summary
        </Button>
      </div>

      {!writeAccess && (
        <p className="rounded-xl border border-white/10 bg-surface/50 px-4 py-3 text-sm text-text-secondary">
          Read-only mode — you can read insights but cannot generate AI summaries or export
          reports.
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <FileText className="h-4 w-4 text-accent" />
            Executive report export
          </CardTitle>
          <CardDescription>
            KPIs, charts, explainability panel
            {summary ? " + AI summary" : " — generate summary first for narrative sections"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={exporting || !writeAccess}
            onClick={() => exportReport("html")}
          >
            <Download className="h-4 w-4" />
            HTML
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={exporting || !writeAccess}
            onClick={() => exportReport("markdown")}
          >
            <Download className="h-4 w-4" />
            Markdown
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={exporting || !writeAccess}
            onClick={() => exportReport("pdf")}
          >
            <Download className="h-4 w-4" />
            PDF
          </Button>
        </CardContent>
        {exportWarnings.length > 0 && (
          <CardContent className="border-t border-white/10 pt-4">
            <ul className="space-y-1 text-xs text-warning">
              {exportWarnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          </CardContent>
        )}
      </Card>

      {!summary && !loading && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-text-secondary">
            Click generate to produce an executive summary from computed KPIs.
          </CardContent>
        </Card>
      )}

      {loading && !summary && (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {summary && (
        <div className="grid gap-4 lg:grid-cols-2">
          <InsightCard title="Executive summary" items={[summary.summary]} full />
          <InsightCard title="Trends" items={summary.trends} />
          <InsightCard title="Risks" items={summary.risks} variant="warning" />
          <InsightCard title="Opportunities" items={summary.opportunities} variant="success" />
          <InsightCard title="Recommendations" items={summary.recommendations} full />
        </div>
      )}
    </div>
  );
}

function InsightCard({
  title,
  items,
  full,
  variant = "default",
}: {
  title: string;
  items: string[];
  full?: boolean;
  variant?: "default" | "success" | "warning";
}) {
  const ring =
    variant === "success"
      ? "ring-success/20"
      : variant === "warning"
        ? "ring-warning/20"
        : "ring-accent/20";

  return (
    <Card className={`${full ? "lg:col-span-2" : ""} ring-1 ${ring}`}>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
        <CardDescription>Grounded in metrics snapshot</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm text-text-primary">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-accent">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
