"use client";

import { useEffect, useState } from "react";
import { Clock, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchAuditLog } from "@/lib/api";
import type { AuditEvent } from "@/types/dashboard";
import { canViewAudit } from "@/lib/permissions";
import { useAuth } from "@/context/AuthContext";

const EVENT_LABELS: Record<string, string> = {
  upload: "Dataset uploaded",
  upload_failed: "Upload failed",
  session_open: "Dataset opened",
  chat: "AI chat",
  chat_clear: "Chat cleared",
  summarize: "AI summary",
  report_export: "Report exported",
  retention_purge: "Retention purge",
};

export function AuditLogPanel() {
  const { user } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canViewAudit(user)) {
      setLoading(false);
      return;
    }
    fetchAuditLog(40)
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [user]);

  if (!canViewAudit(user)) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Shield className="h-4 w-4 text-accent" />
          Audit trail
        </CardTitle>
        <p className="text-xs text-text-secondary">
          Who did what — uploads, AI actions, exports (demo logging)
        </p>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {loading ? (
          <p className="py-6 text-center text-sm text-text-secondary">Loading…</p>
        ) : events.length === 0 ? (
          <p className="py-6 text-center text-sm text-text-secondary">No events yet.</p>
        ) : (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-text-secondary">
                <th className="pb-2 pr-3 font-medium">Time</th>
                <th className="pb-2 pr-3 font-medium">Event</th>
                <th className="pb-2 pr-3 font-medium">User</th>
                <th className="pb-2 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-white/5">
                  <td className="py-2 pr-3 whitespace-nowrap text-text-secondary">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-3 text-text-primary">
                    {EVENT_LABELS[e.event_type] ?? e.event_type}
                  </td>
                  <td className="py-2 pr-3 text-text-secondary">{e.actor}</td>
                  <td className="py-2 max-w-xs truncate text-text-secondary">
                    {formatDetail(e)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function formatDetail(e: AuditEvent): string {
  const d = e.detail;
  if (e.event_type === "chat" && d.question_preview) {
    return String(d.question_preview);
  }
  if (d.source_file) return String(d.source_file);
  if (d.sources && Array.isArray(d.sources)) {
    return (d.sources as string[]).slice(0, 3).join(", ");
  }
  if (d.deleted_sessions && Array.isArray(d.deleted_sessions)) {
    return `${(d.deleted_sessions as string[]).length} sessions removed`;
  }
  return e.session_id ?? "—";
}

export function RetentionNotice() {
  const [days, setDays] = useState<number | null>(null);
  const [expiring, setExpiring] = useState(0);

  useEffect(() => {
    import("@/lib/api")
      .then(({ fetchRetentionPolicy }) => fetchRetentionPolicy())
      .then((p) => {
        setDays(p.retention_days);
        setExpiring(p.expiring_soon.length);
      })
      .catch(() => {});
  }, []);

  if (days === null) return null;

  return (
    <div className="flex items-start gap-2 rounded-xl border border-white/10 bg-surface/50 px-4 py-3 text-xs text-text-secondary">
      <Clock className="mt-0.5 h-4 w-4 shrink-0 text-text-secondary" />
      <p>
        Data retention: datasets auto-delete after <strong>{days} days</strong>.
        {expiring > 0 && (
          <>
            {" "}
            <span className="text-warning">
              {expiring} dataset(s) expiring within 14 days — export reports if needed.
            </span>
          </>
        )}
      </p>
    </div>
  );
}
