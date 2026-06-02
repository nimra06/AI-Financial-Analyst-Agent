"use client";

import { ChevronDown, Database, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/context/DashboardContext";
import { useDropdownPosition } from "@/hooks/useDropdownPosition";

export function WorkspaceSwitcher() {
  const { dashboard, sessions, loadSession, setActiveSection } = useDashboard();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (!dashboard) {
    return (
      <button
        type="button"
        onClick={() => setActiveSection("data")}
        className="flex items-center gap-2 rounded-xl border border-dashed border-white/15 px-3 py-2 text-sm text-text-secondary transition hover:border-accent/40 hover:text-text-primary"
      >
        <Database className="h-4 w-4" />
        Import dataset
      </button>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex max-w-xs items-center gap-2 rounded-xl border border-white/10 bg-card/60 px-3 py-2 text-left transition hover:border-accent/30 sm:max-w-sm"
      >
        <Database className="h-4 w-4 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">
            {dashboard.source_file}
          </p>
          <p className="truncate text-xs text-text-secondary">
            {dashboard.period_count} periods · {dashboard.kpis.latest_month}
          </p>
        </div>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-text-secondary transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-2 w-72 overflow-hidden rounded-xl border border-white/10 bg-surface shadow-xl">
          <div className="border-b border-white/10 px-3 py-2 text-xs font-medium text-text-secondary">
            Switch dataset
          </div>
          <ul className="max-h-56 overflow-y-auto py-1">
            {sessions.map((s) => (
              <li key={s.session_id}>
                <button
                  type="button"
                  onClick={() => {
                    loadSession(s.session_id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full flex-col px-3 py-2 text-left text-sm transition hover:bg-white/5",
                    dashboard.session_id === s.session_id && "bg-accent/10"
                  )}
                >
                  <span className="truncate font-medium text-text-primary">
                    {s.source_file}
                  </span>
                  <span className="text-xs text-text-secondary">
                    {s.period_count} periods · {s.latest_month}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => {
              setActiveSection("data");
              setOpen(false);
            }}
            className="w-full border-t border-white/10 px-3 py-2.5 text-left text-sm text-accent hover:bg-white/5"
          >
            + Import new dataset
          </button>
        </div>
      )}
    </div>
  );
}

export function UserMenu() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const anchorRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const position = useDropdownPosition(anchorRef, open);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (anchorRef.current?.contains(target)) return;
      if (panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  const initials = user.name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const menuPanel = open && position && (
    <div
      ref={panelRef}
      role="menu"
      className="fixed z-[200] w-56 overflow-hidden rounded-xl border border-white/10 bg-surface py-1 shadow-2xl ring-1 ring-black/20"
      style={{ top: position.top, right: position.right }}
    >
      <div className="border-b border-white/10 px-3 py-2.5">
        <p className="text-sm font-medium text-text-primary">{user.name}</p>
        <p className="truncate text-xs text-text-secondary">{user.email}</p>
        <p className="mt-1 text-[10px] uppercase tracking-wide text-accent">{user.role}</p>
      </div>
      <button
        type="button"
        role="menuitem"
        onClick={() => {
          signOut();
          setOpen(false);
        }}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-sm text-text-primary hover:bg-white/10"
      >
        <LogOut className="h-4 w-4 shrink-0" />
        Sign out
      </button>
    </div>
  );

  return (
    <>
      <button
        ref={anchorRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-xl border border-white/10 px-2 py-1.5 transition hover:bg-white/5"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/20 text-xs font-semibold text-accent">
          {initials}
        </span>
        <span className="hidden text-sm text-text-primary md:block">{user.name}</span>
        <ChevronDown
          className={cn("h-4 w-4 text-text-secondary transition", open && "rotate-180")}
        />
      </button>
      {mounted && menuPanel ? createPortal(menuPanel, document.body) : null}
    </>
  );
}
