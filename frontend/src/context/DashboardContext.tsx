"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type {
  ChatMessage,
  DashboardData,
  ExecutiveSummary,
  ForecastPayload,
  SessionMeta,
  UploadValidation,
} from "@/types/dashboard";
import {
  UploadValidationError,
  clearChatHistory,
  fetchChatHistory,
  generateForecast,
  generateSummary,
  enqueueForecastJob,
  pollJob,
  getSession,
  listSessions,
  sendChat,
  uploadFile,
} from "@/lib/api";
import {
  clearActiveSession,
  persistActiveSession,
  readActiveSessionId,
} from "@/lib/workspace";

interface DashboardContextValue {
  dashboard: DashboardData | null;
  sessions: SessionMeta[];
  loading: boolean;
  error: string | null;
  summary: ExecutiveSummary | null;
  forecast: ForecastPayload | null;
  chatMessages: ChatMessage[];
  activeSection: string;
  setActiveSection: (s: string) => void;
  upload: (file: File) => Promise<void>;
  loadSession: (id: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
  runSummary: () => Promise<void>;
  runForecast: (metric: string, horizon: number) => Promise<void>;
  askChat: (message: string) => Promise<void>;
  clearChat: () => Promise<void>;
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  workspaceLoading: boolean;
  initWorkspace: () => Promise<void>;
  uploadValidation: UploadValidation | null;
  clearUploadValidation: () => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [forecast, setForecast] = useState<ForecastPayload | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [activeSection, setActiveSection] = useState("overview");
  const [chatOpen, setChatOpen] = useState(false);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [uploadValidation, setUploadValidation] = useState<UploadValidation | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch {
      /* API may be offline */
    }
  }, []);

  const loadChatHistory = useCallback(async (sessionId: string) => {
    try {
      const messages = await fetchChatHistory(sessionId);
      setChatMessages(messages);
    } catch {
      setChatMessages([]);
    }
  }, []);

  const initWorkspace = useCallback(async () => {
    setWorkspaceLoading(true);
    setError(null);
    try {
      const list = await listSessions();
      setSessions(list);
      if (list.length === 0) {
        setDashboard(null);
        setChatMessages([]);
        clearActiveSession();
        return;
      }
      const stored = readActiveSessionId();
      const sessionId =
        stored && list.some((s) => s.session_id === stored)
          ? stored
          : list[0].session_id;
      const data = await getSession(sessionId, { skipAudit: true });
      setDashboard(data);
      persistActiveSession(sessionId);
      await loadChatHistory(sessionId);
    } catch {
      /* API may be offline — user can upload manually */
    } finally {
      setWorkspaceLoading(false);
    }
  }, [loadChatHistory]);

  useEffect(() => {
    void initWorkspace();
  }, [initWorkspace]);

  const upload = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      setUploadValidation(null);
      setSummary(null);
      setForecast(null);
      try {
        const data = await uploadFile(file);
        setDashboard(data);
        persistActiveSession(data.session_id);
        setChatMessages([]);
        await refreshSessions();
        setActiveSection("overview");
      } catch (e) {
        if (e instanceof UploadValidationError) {
          setUploadValidation({
            errors: e.errors,
            warnings: e.warnings,
            row_count: e.rowCount,
          });
          setActiveSection("data");
        } else {
          setError(e instanceof Error ? e.message : "Upload failed");
        }
      } finally {
        setLoading(false);
      }
    },
    [refreshSessions]
  );

  const loadSession = useCallback(
    async (id: string) => {
      setLoading(true);
      setError(null);
      setUploadValidation(null);
      try {
        const data = await getSession(id);
        setDashboard(data);
        persistActiveSession(id);
        setSummary(null);
        setForecast(null);
        await loadChatHistory(id);
        setActiveSection("overview");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load session");
      } finally {
        setLoading(false);
      }
    },
    [loadChatHistory]
  );

  const runSummary = useCallback(async () => {
    if (!dashboard) return;
    setLoading(true);
    setError(null);
    try {
      const s = await generateSummary(dashboard.snapshot, dashboard.session_id);
      setSummary(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Summary failed");
    } finally {
      setLoading(false);
    }
  }, [dashboard]);

  const runForecast = useCallback(
    async (metric: string, horizon: number) => {
      if (!dashboard) return;
      setLoading(true);
      setError(null);
      try {
        if (horizon >= 12) {
          const { job_id } = await enqueueForecastJob(
            dashboard.monthly_records,
            metric,
            horizon
          );
          const f = await pollJob(job_id, (result) => result.forecast as ForecastPayload);
          setForecast(f);
        } else {
          const f = await generateForecast(dashboard.monthly_records, metric, horizon);
          setForecast(f);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Forecast failed");
      } finally {
        setLoading(false);
      }
    },
    [dashboard]
  );

  const askChat = useCallback(
    async (message: string) => {
      if (!dashboard) return;
      const userMsg: ChatMessage = { role: "user", content: message };
      setChatMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      try {
        const result = await sendChat(message, dashboard, chatMessages);
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.answer,
            sources: result.sources,
          },
        ]);
      } catch (e) {
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${e instanceof Error ? e.message : "Chat failed"}`,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [dashboard, chatMessages]
  );

  const clearChat = useCallback(async () => {
    if (!dashboard) {
      setChatMessages([]);
      return;
    }
    try {
      await clearChatHistory(dashboard.session_id);
    } catch {
      /* ignore */
    }
    setChatMessages([]);
  }, [dashboard]);

  const clearUploadValidation = useCallback(() => setUploadValidation(null), []);

  return (
    <DashboardContext.Provider
      value={{
        dashboard,
        sessions,
        loading,
        error,
        summary,
        forecast,
        chatMessages,
        activeSection,
        setActiveSection,
        upload,
        loadSession,
        refreshSessions,
        runSummary,
        runForecast,
        askChat,
        clearChat,
        chatOpen,
        setChatOpen,
        workspaceLoading,
        initWorkspace,
        uploadValidation,
        clearUploadValidation,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
