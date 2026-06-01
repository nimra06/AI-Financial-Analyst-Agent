"use client";

import type { DashboardData } from "@/types/dashboard";

/** Render metric sources as clickable chips tied to KPI snapshot values. */
export function SourceChips({
  sources,
  dashboard,
}: {
  sources: string[];
  dashboard?: DashboardData | null;
}) {
  if (!sources.length) return null;

  const metrics = dashboard?.kpis ?? {};

  const resolveHint = (source: string): string | undefined => {
    const lower = source.toLowerCase();
    for (const key of Object.keys(metrics)) {
      if (lower.includes(key.replace(/_/g, " ")) || lower.includes(key)) {
        const val = metrics[key as keyof typeof metrics];
        if (val !== null && val !== undefined) {
          return `${key}: ${String(val)}`;
        }
      }
    }
    return undefined;
  };

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {sources.map((source, i) => {
        const hint = resolveHint(source);
        return (
          <span
            key={i}
            title={hint ?? "Computed from uploaded dataset"}
            className="cursor-help rounded-full bg-accent/15 px-2 py-0.5 text-[10px] font-medium text-accent ring-1 ring-accent/25"
          >
            {source}
          </span>
        );
      })}
    </div>
  );
}
