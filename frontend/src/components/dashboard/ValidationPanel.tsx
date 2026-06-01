"use client";

import { AlertTriangle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { UploadValidation } from "@/types/dashboard";

export function ValidationPanel({
  validation,
  onDismiss,
}: {
  validation: UploadValidation;
  onDismiss?: () => void;
}) {
  return (
    <Card className="border-red-500/30 bg-red-500/5">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base text-red-200">
            <XCircle className="h-5 w-5" />
            Import validation failed
          </CardTitle>
          {validation.row_count > 0 && (
            <p className="mt-1 text-xs text-text-secondary">
              {validation.row_count} rows scanned — fix the issues below and re-upload.
            </p>
          )}
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
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="max-h-48 space-y-1.5 overflow-y-auto text-sm text-red-100">
          {validation.errors.map((err, i) => (
            <li key={i} className="rounded-lg bg-red-500/10 px-3 py-2 font-mono text-xs">
              {err}
            </li>
          ))}
        </ul>
        {validation.warnings.length > 0 && (
          <div>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-warning">
              <AlertTriangle className="h-3.5 w-3.5" />
              Warnings
            </p>
            <ul className="space-y-1 text-xs text-text-secondary">
              {validation.warnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-text-secondary">
          Need a template? Download{" "}
          <a
            href="/samples/template_monthly_pl.csv"
            download
            className="text-accent hover:underline"
          >
            template_monthly_pl.csv
          </a>
        </p>
      </CardContent>
    </Card>
  );
}
