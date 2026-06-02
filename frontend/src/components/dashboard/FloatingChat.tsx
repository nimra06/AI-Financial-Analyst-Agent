"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, MessageCircle, Minus, Send, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { SourceChips } from "@/components/dashboard/SourceChips";
import { useAuth } from "@/context/AuthContext";
import { useDashboard } from "@/context/DashboardContext";
import { canWrite } from "@/lib/permissions";

const DATASET_SUGGESTIONS = [
  "Which month had the highest revenue?",
  "Why did net profit change?",
  "What anomalies were detected?",
];

const FREELANCE_SUGGESTIONS = [
  "Who are my best clients?",
  "Is my income too concentrated on a few clients?",
  "What file should I upload for monthly trends?",
];

const GENERAL_SUGGESTIONS = [
  "What data should I upload?",
  "How does this app work?",
  "What is gross margin?",
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
    uploadValidation,
  } = useDashboard();
  const { user } = useAuth();
  const writeAccess = canWrite(user);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const hasFreelance = Boolean(uploadValidation?.freelance_summary);
  const chatMode = hasFreelance ? "freelance" : dashboard ? "dataset" : "general";

  const suggestions =
    chatMode === "dataset"
      ? DATASET_SUGGESTIONS
      : chatMode === "freelance"
        ? FREELANCE_SUGGESTIONS
        : GENERAL_SUGGESTIONS;

  const canChat = writeAccess && !workspaceLoading;

  useEffect(() => {
    if (chatOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, loading, chatOpen]);

  const submit = async (text: string) => {
    if (!text.trim() || loading || !canChat) return;
    setInput("");
    await askChat(text.trim());
  };

  const statusLabel =
    chatMode === "dataset"
      ? `${dashboard!.source_file} · ${dashboard!.kpis.latest_month}`
      : chatMode === "freelance"
        ? "Client billing insights"
        : "General assistant";

  const welcomeText =
    chatMode === "dataset"
      ? "Ask about revenue, profit, expenses, or forecasts — answers use your loaded numbers."
      : chatMode === "freelance"
        ? "I can discuss your Upwork-style client list: top earners, concentration, and what to upload next."
        : "No monthly file loaded yet — I can still help with formats, metrics, and how to use the app.";

  return (
    <div className="pointer-events-none fixed bottom-0 right-0 z-50 flex flex-col items-end p-4 sm:p-6">
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
            <div className="flex items-center justify-between border-b border-white/[0.06] bg-surface/90 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/20 ring-1 ring-accent/30">
                  <Bot className="h-4 w-4 text-accent" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">AI Analyst</p>
                  <p className="text-xs text-text-secondary">
                    {workspaceLoading ? "Loading…" : statusLabel}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={clearChat}
                  className="rounded-lg p-2 text-text-secondary transition hover:bg-white/5 hover:text-text-primary"
                  title="Clear chat"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
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

            <div className="flex-1 overflow-y-auto bg-background/40 p-4">
              {workspaceLoading ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                  <p className="text-sm text-text-secondary">Restoring workspace…</p>
                </div>
              ) : (
                <>
                  {chatMessages.length === 0 && (
                    <div className="mb-4 space-y-3">
                      <div
                        className={cn(
                          "rounded-xl border px-3 py-2.5 text-xs leading-relaxed",
                          chatMode === "dataset"
                            ? "border-accent/20 bg-accent/5 text-text-primary"
                            : chatMode === "freelance"
                              ? "border-amber-500/20 bg-amber-500/5 text-text-primary"
                              : "border-white/10 bg-surface/50 text-text-secondary"
                        )}
                      >
                        {chatMode === "dataset" && (
                          <>
                            Connected to{" "}
                            <span className="font-medium">{dashboard!.source_file}</span>
                          </>
                        )}
                        {chatMode === "freelance" && (
                          <span className="font-medium">Using your client billing upload</span>
                        )}
                        {chatMode === "general" && (
                          <span className="font-medium">General mode</span>
                        )}
                        <p className="mt-1.5 text-text-secondary">{welcomeText}</p>
                      </div>
                      {sessions.length > 0 && chatMode === "general" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="w-full"
                          onClick={() => loadSession(sessions[0].session_id)}
                        >
                          Open latest saved dataset
                        </Button>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {suggestions.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => submit(s)}
                            disabled={!canChat}
                            className="rounded-full border border-white/10 bg-surface/80 px-3 py-1.5 text-left text-xs text-text-secondary transition hover:border-accent/40 hover:bg-accent/10 hover:text-text-primary disabled:opacity-50"
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
                        {msg.role === "assistant" &&
                          msg.sources &&
                          dashboard &&
                          chatMode === "dataset" && (
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
                disabled={!canChat || loading}
                placeholder={
                  !writeAccess
                    ? "Read-only mode"
                    : chatMode === "dataset"
                      ? `Ask about ${dashboard!.source_file}…`
                      : chatMode === "freelance"
                        ? "Ask about your clients…"
                        : "Ask anything…"
                }
                className="flex-1 rounded-full border border-white/10 bg-background px-4 py-2.5 text-sm text-text-primary placeholder:text-text-secondary focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30 disabled:opacity-50"
              />
              <Button
                type="submit"
                size="icon"
                className="h-10 w-10 shrink-0 rounded-full"
                disabled={!canChat || loading}
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </>
        )}
      </div>

      <button
        type="button"
        onClick={() => setChatOpen(!chatOpen)}
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
            {(dashboard || hasFreelance) && chatMessages.length > 0 && (
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
