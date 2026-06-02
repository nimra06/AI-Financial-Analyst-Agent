"use client";

import { useCallback, useState } from "react";
import { FileSpreadsheet, Lock, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDashboard } from "@/context/DashboardContext";
import { useAuth } from "@/context/AuthContext";
import { canWrite } from "@/lib/permissions";

export function FileUpload({ compact = false }: { compact?: boolean }) {
  const { upload, loading } = useDashboard();
  const { user } = useAuth();
  const writeAccess = canWrite(user);
  const [drag, setDrag] = useState(false);

  const onDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      if (!writeAccess) return;
      const file = e.dataTransfer.files[0];
      if (file) await upload(file);
    },
    [upload, writeAccess]
  );

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!writeAccess) return;
    const file = e.target.files?.[0];
    if (file) await upload(file);
  };

  if (!writeAccess) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-card/20",
          compact ? "p-6" : "p-12"
        )}
      >
        <Lock className="mb-3 h-8 w-8 text-text-secondary" />
        <p className="text-sm font-medium text-text-primary">Read-only mode</p>
        <p className="mt-1 text-xs text-text-secondary">
          Sign in as Analyst or Admin to import datasets
        </p>
      </div>
    );
  }

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={cn(
        "group flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed transition-all duration-200",
        compact ? "p-6" : "p-12",
        drag
          ? "border-accent bg-accent/10"
          : "border-white/15 bg-card/40 hover:border-accent/40 hover:bg-accent/5"
      )}
    >
      <input
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        disabled={loading}
        onChange={onFile}
      />
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/15 ring-1 ring-accent/25 transition group-hover:scale-105">
        {loading ? (
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        ) : (
          <Upload className="h-6 w-6 text-accent" />
        )}
      </div>
      <p className="text-base font-medium text-text-primary">
        Drop your financial file here
      </p>
      <p className="mt-1 text-sm text-text-secondary">
        CSV or Excel · Monthly P&L format
      </p>
      <div className="mt-4 flex items-center gap-2 text-xs text-text-secondary">
        <FileSpreadsheet className="h-3.5 w-3.5" />
        date, revenue, cogs, opex
      </div>
    </label>
  );
}
