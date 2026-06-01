"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, MessageCircle, Minus, Send, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SourceChips } from "@/components/dashboard/SourceChips";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/context/DashboardContext";
import { canWrite } from "@/lib/permissions";

const SUGGESTIONS = [
  "Which month had the highest revenue?",
  "Why did net profit change?",
  "What anomalies were detected?",
  "Predict next quarter revenue",
];

export function FloatingChat() {
  const {
    dashboard,
    sessions,
    chatMessages,
    askChat,
    clearChat,
    loading,
    chatOpen,
    setChatOpen,
    setActiveSection,
    workspaceLoading,
    loadSession,
  } = useDashboard();
  const { user } = useAuth();
  const writeAccess = canWrite(user);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, loading, chatOpen]);

  const submit = async (text: string) => {
    if (!text.trim() || loading || !dashboard || !writeAccess) return;
    setInput("");
    await askChat(text.trim());
  };

  const toggle = () => setChatOpen(!chatOpen);

  return (
    <div className="pointer-events-none fixed bottom-0 right-0 z-50 flex flex-col items-end p-4 sm:p-6">
      {/* Chat panel — Messenger-style */}
      <div
        className={cn(
          "pointer-events-auto mb-4 flex origin-bottom-right flex-col overflow-hidden rounded-2xl border border-white/10 bg-card shadow-2xl ring-1 ring-white/5 transition-all duration-300 ease-out",
          chatOpen
            ? "h-[min(520px,calc(100vh-8rem))] w-[min(400px,calc(100vw-2rem))] scale-100 opacity-100"
            : "h-0 w-0 scale-95 opacity-0"
        )}
        aria-hidden={!chatOpen}
      >
        {chatOpen && (
          <>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/[0.06] bg-surface/90 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/20 ring-1 ring-accent/30">
                  <Bot className="h-4 w-4 text-accent" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">AI Analyst</p>
                  <p className="text-xs text-text-secondary">
                    {workspaceLoading
                      ? "Loading workspace…"
                      : dashboard
                        ? `${dashboard.source_file} · ${dashboard.kpis.latest_month}`
                        : sessions.length > 0
                          ? "Select a dataset"
                          : "No dataset loaded"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {dashboard && (
                  <button
                    type="button"
                    onClick={clearChat}
                    className="rounded-lg p-2 text-text-secondary transition hover:bg-white/5 hover:text-text-primary"
                    title="Clear chat"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setChatOpen(false)}
                  className="rounded-lg p-2 text-text-secondary transition hover:bg-white/5 hover:text-text-primary"
                  title="Minimize"
                >
                  <Minus className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto bg-background/40 p-4">
              {workspaceLoading ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                  <p className="text-sm text-text-secondary">Restoring your dataset…</p>
                </div>
              ) : !dashboard ? (
                <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
                  <p className="text-sm text-text-secondary">
                    {sessions.length > 0
                      ? "Open a saved dataset to start asking questions."
                      : "Add a financial file in Data to enable the assistant."}
                  </p>
                  {sessions.length > 0 ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => loadSession(sessions[0].session_id)}
                    >
                      Open latest dataset
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setChatOpen(false);
                        setActiveSection("data");
                      }}
                    >
                      Go to Data
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  {chatMessages.length === 0 && (
                    <div className="mb-4 space-y-2">
                      <div className="rounded-xl border border-accent/20 bg-accent/5 px-3 py-2.5 text-center text-xs text-text-primary">
                        Connected to{" "}
                        <span className="font-medium">{dashboard.source_file}</span> (
                        {dashboard.period_count} periods · latest{" "}
                        {dashboard.kpis.latest_month})
                      </div>
                      <p className="text-center text-xs text-text-secondary">
                        Ask about revenue, profit, expenses, forecasts, or anomalies
                      </p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {SUGGESTIONS.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => submit(s)}
                            className="rounded-full border border-white/10 bg-surface/80 px-3 py-1.5 text-xs text-text-secondary transition hover:border-accent/40 hover:bg-accent/10 hover:text-text-primary"
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="space-y-3">
                    {chatMessages.map((msg, i) => (
                      <div
                        key={i}
                        className={cn(
                          "max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm",
                          msg.role === "user"
                            ? "ml-auto rounded-br-md bg-accent text-white"
                            : "rounded-bl-md bg-surface ring-1 ring-white/10 text-text-primary"
                        )}
                      >
                        <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        {msg.role === "assistant" && msg.sources && (
                          <SourceChips sources={msg.sources} dashboard={dashboard} />
                        )}
                      </div>
                    ))}
                    {loading && (
                      <div className="flex gap-1 rounded-2xl rounded-bl-md bg-surface px-4 py-3 ring-1 ring-white/10">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-text-secondary [animation-delay:-0.3s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-text-secondary [animation-delay:-0.15s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-text-secondary" />
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </>
              )}
            </div>

            {/* Input */}
            <form
              className="flex gap-2 border-t border-white/[0.06] bg-surface/90 p-3"
              onSubmit={(e) => {
                e.preventDefault();
                submit(input);
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!dashboard || loading || workspaceLoading || !writeAccess}
                placeholder={
                  !writeAccess
                    ? "Viewer role — read-only"
                    : workspaceLoading
                      ? "Loading dataset…"
                      : dashboard
                        ? `Ask about ${dashboard.source_file}…`
                        : "Load a dataset to chat…"
                }
                className="flex-1 rounded-full border border-white/10 bg-background px-4 py-2.5 text-sm text-text-primary placeholder:text-text-secondary focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30 disabled:opacity-50"
              />
              <Button
                type="submit"
                size="icon"
                className="h-10 w-10 shrink-0 rounded-full"
                disabled={!dashboard || loading}
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </>
        )}
      </div>

      {/* FAB */}
      <button
        type="button"
        onClick={toggle}
        className={cn(
          "pointer-events-auto relative flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all duration-300 hover:scale-105 active:scale-95",
          chatOpen
            ? "bg-surface text-text-primary ring-1 ring-white/15"
            : "bg-accent text-white shadow-accent/25 hover:bg-blue-500"
        )}
        aria-label={chatOpen ? "Close chat" : "Open AI assistant"}
      >
        {chatOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <>
            <MessageCircle className="h-6 w-6" />
            {dashboard && chatMessages.length > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-success text-[10px] font-bold text-white ring-2 ring-background">
                {chatMessages.filter((m) => m.role === "assistant").length || ""}
              </span>
            )}
          </>
        )}
      </button>
    </div>
  );
}
