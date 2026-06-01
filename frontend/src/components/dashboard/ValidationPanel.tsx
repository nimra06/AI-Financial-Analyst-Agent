"use client";

import { ArrowRight, FileSpreadsheet, MessageCircle, Sparkles, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { UploadValidation } from "@/types/dashboard";

export function ValidationPanel({
  validation,
  onDismiss,
  onAskAi,
}: {
  validation: UploadValidation;
  onDismiss?: () => void;
  onAskAi?: () => void;
}) {
  const isFreelance = validation.detected_format === "freelance_client_billing";
  const summary = validation.freelance_summary;
  const topClients = summary?.top_clients ?? [];
  const total = summary?.total_lifetime ?? 0;
  const clientCount = summary?.client_count ?? validation.row_count;

  if (isFreelance && summary) {
    return (
      <div className="space-y-4">
        <Card className="overflow-hidden border-amber-500/30 bg-gradient-to-br from-amber-500/10 via-card to-card">
          <CardContent className="p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-500/20 ring-1 ring-amber-500/30">
                  <FileSpreadsheet className="h-6 w-6 text-amber-400" />
                </div>
                <div>
                  <Badge variant="warning" className="mb-2">
                    Client billing file
                  </Badge>
                  <h3 className="text-lg font-semibold text-text-primary">
                    We read your file — different format than monthly P&L
                  </h3>
                  <p className="mt-1 max-w-xl text-sm text-text-secondary">
                    This looks like lifetime earnings per client (e.g. Upwork). Charts and KPIs
                    need monthly rows with <span className="text-text-primary">date</span> and{" "}
                    <span className="text-text-primary">revenue</span>.
                  </p>
                </div>
              </div>
              {onDismiss && (
                <button
                  type="button"
                  onClick={onDismiss}
                  className="text-xs text-text-secondary hover:text-text-primary"
                >
                  Dismiss
                </button>
              )}
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <Stat label="Lifetime total" value={`$${total.toLocaleString()}`} />
              <Stat label="Clients" value={String(clientCount)} />
              <Stat
                label="Top client share"
                value={
                  topClients[0]
                    ? `${topClients[0].share_pct}% · ${topClients[0].client}`
                    : "—"
                }
              />
            </div>

            {topClients.length > 0 && (
              <div className="mt-6">
                <p className="mb-3 text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Your best clients
                </p>
                <div className="flex flex-wrap gap-2">
                  {topClients.map((row, i) => (
                    <div
                      key={row.client}
                      className="rounded-xl border border-white/10 bg-surface/80 px-3 py-2"
                    >
                      <p className="text-sm font-medium text-text-primary">
                        {i + 1}. {row.client}
                      </p>
                      <p className="text-xs text-text-secondary">
                        ${row.amount.toLocaleString()} · {row.share_pct}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              {onAskAi && (
                <Button onClick={onAskAi} className="gap-2">
                  <MessageCircle className="h-4 w-4" />
                  Ask AI about this file
                </Button>
              )}
              <a href="/samples/template_monthly_pl.csv" download>
                <Button variant="secondary" className="gap-2">
                  <Upload className="h-4 w-4" />
                  Download monthly template
                </Button>
              </a>
            </div>

            <p className="mt-4 flex items-start gap-2 text-xs text-text-secondary">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
              Month-over-month trends need a dated export. The AI assistant can still discuss
              your top clients and concentration risk from this file.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Card className="border-red-500/30 bg-red-500/5">
      <CardContent className="space-y-4 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-red-200">Wrong file type</h3>
            <p className="mt-1 text-sm text-text-secondary">
              This doesn&apos;t match our monthly financial format ({validation.row_count} rows
              scanned).
            </p>
          </div>
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="text-xs text-text-secondary hover:text-text-primary"
            >
              Dismiss
            </button>
          )}
        </div>
        <ul className="space-y-2 text-sm text-text-primary">
          {validation.errors.map((err, i) => (
            <li key={i} className="flex gap-2">
              <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />
              {err}
            </li>
          ))}
        </ul>
        <a href="/samples/template_monthly_pl.csv" download>
          <Button variant="secondary" size="sm">
            Get the correct template
          </Button>
        </a>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-surface/60 px-4 py-3">
      <p className="text-xs text-text-secondary">{label}</p>
      <p className="mt-1 text-lg font-semibold text-text-primary">{value}</p>
    </div>
  );
}
