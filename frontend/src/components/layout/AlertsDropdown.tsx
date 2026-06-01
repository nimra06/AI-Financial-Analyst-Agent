"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchAlerts, markAlertsRead } from "@/lib/api";
import type { AlertItem } from "@/types/dashboard";
import { useDashboard } from "@/context/DashboardContext";

export function AlertsDropdown() {
  const { dashboard } = useDashboard();
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  const load = () => {
    fetchAlerts(dashboard?.session_id)
      .then(setAlerts)
      .catch(() => setAlerts([]));
  };

  useEffect(() => {
    load();
  }, [dashboard?.session_id]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = alerts.filter((a) => !a.read_at).length;

  const openPanel = () => {
    setOpen(!open);
    if (!open) load();
  };

  const markRead = async () => {
    await markAlertsRead(dashboard?.session_id);
    load();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={openPanel}
        className="relative rounded-xl border border-white/10 p-2 text-text-secondary transition hover:bg-white/5 hover:text-text-primary"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-warning text-[10px] font-bold text-background">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-white/10 bg-surface shadow-xl">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
            <p className="text-sm font-medium text-text-primary">Alerts</p>
            {unread > 0 && (
              <button
                type="button"
                onClick={markRead}
                className="text-xs text-accent hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          <ul className="max-h-72 overflow-y-auto">
            {alerts.length === 0 ? (
              <li className="px-4 py-6 text-center text-xs text-text-secondary">
                No active alerts
              </li>
            ) : (
              alerts.map((a) => (
                <li
                  key={a.id}
                  className={cn(
                    "border-b border-white/5 px-4 py-3",
                    !a.read_at && "bg-warning/5"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-text-primary">{a.title}</p>
                    <span
                      className={cn(
                        "shrink-0 rounded px-1.5 py-0.5 text-[10px] uppercase",
                        a.severity === "high" && "bg-red-500/20 text-red-200",
                        a.severity === "medium" && "bg-warning/20 text-warning",
                        a.severity === "low" && "bg-white/10 text-text-secondary"
                      )}
                    >
                      {a.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-text-secondary">{a.message}</p>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
