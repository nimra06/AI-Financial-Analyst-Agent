import type {
  AuditEvent,
  ChatMessage,
  DashboardData,
  ExecutiveSummary,
  ForecastPayload,
  ReportPayload,
  RetentionPolicy,
  SessionMeta,
  UploadValidation,
  WhyInsight,
} from "@/types/dashboard";
import type { DemoUser } from "@/lib/auth";
import { readAccessToken, readDemoUser, clearAuthSession } from "@/lib/auth";

/** Absolute API origin — adds https:// if the env var omits a protocol. */
function normalizeApiBase(raw: string | undefined): string {
  const fallback = "http://localhost:8000";
  const value = (raw ?? fallback).trim();
  if (!value) return fallback;
  if (/^https?:\/\//i.test(value)) return value.replace(/\/$/, "");
  return `https://${value.replace(/^\/+/, "").replace(/\/$/, "")}`;
}

const API_BASE = normalizeApiBase(process.env.NEXT_PUBLIC_API_URL);

export class UploadValidationError extends Error {
  errors: string[];
  warnings: string[];
  rowCount: number;
  detectedFormat?: string | null;
  freelanceInsights: string[];
  freelanceSummary?: UploadValidation["freelance_summary"];

  constructor(
    errors: string[],
    warnings: string[],
    rowCount: number,
    extra?: Pick<
      UploadValidation,
      "detected_format" | "freelance_insights" | "freelance_summary"
    >
  ) {
    super(errors[0] ?? "Validation failed");
    this.name = "UploadValidationError";
    this.errors = errors;
    this.warnings = warnings;
    this.rowCount = rowCount;
    this.detectedFormat = extra?.detected_format;
    this.freelanceInsights = extra?.freelance_insights ?? [];
    this.freelanceSummary = extra?.freelance_summary ?? undefined;
  }
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = readAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    return headers;
  }
  const user = readDemoUser();
  if (user) {
    headers["X-Demo-User"] = `${user.name} <${user.email}>`;
    headers["X-Demo-Role"] = user.role;
  }
  return headers;
}

function apiErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === "object" && err !== null && "detail" in err) {
    const detail = (err as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function handleUnauthorized(res: Response, errBody: unknown): void {
  if (res.status !== 401 || !readAccessToken()) return;
  clearAuthSession();
  const detail = apiErrorMessage(errBody, "");
  if (detail.toLowerCase().includes("token")) {
    throw new Error("Session expired. Please sign in again.");
  }
  throw new Error("Please sign in again.");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = { ...authHeaders(), ...(init?.headers as Record<string, string>) };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    handleUnauthorized(res, err);
    throw new Error(apiErrorMessage(err, res.statusText));
  }
  return res.json() as Promise<T>;
}

export async function uploadFile(file: File): Promise<DashboardData> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/upload`, {
    method: "POST",
    body: form,
    headers: authHeaders(),
  });
  if (res.status === 422) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail as UploadValidation | undefined;
    if (detail?.errors) {
      throw new UploadValidationError(
        detail.errors,
        detail.warnings ?? [],
        detail.row_count ?? 0,
        {
          detected_format: detail.detected_format,
          freelance_insights: detail.freelance_insights,
          freelance_summary: detail.freelance_summary,
        }
      );
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    handleUnauthorized(res, err);
    throw new Error(apiErrorMessage(err, res.statusText));
  }
  const data = (await res.json()) as { dashboard: DashboardData };
  return data.dashboard;
}

export async function listSessions(): Promise<SessionMeta[]> {
  return request<SessionMeta[]>("/api/v1/sessions");
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request<{ status: string }>(`/api/v1/sessions/${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export async function getSession(
  sessionId: string,
  options?: { skipAudit?: boolean }
): Promise<DashboardData> {
  const headers = authHeaders(
    options?.skipAudit ? { "X-Skip-Audit": "1" } : undefined
  );
  const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    handleUnauthorized(res, err);
    throw new Error(apiErrorMessage(err, res.statusText));
  }
  return res.json() as Promise<DashboardData>;
}

export async function fetchChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const res = await request<{ messages: ChatMessage[] }>(
    `/api/v1/sessions/${sessionId}/chat`
  );
  return res.messages.map((m) => ({
    role: m.role,
    content: m.content,
    sources: m.sources,
  }));
}

export async function clearChatHistory(sessionId: string): Promise<void> {
  await request<{ status: string }>(`/api/v1/sessions/${sessionId}/chat`, {
    method: "DELETE",
  });
}

export async function generateSummary(
  snapshot: Record<string, unknown>,
  sessionId?: string
): Promise<ExecutiveSummary> {
  const res = await request<{ summary: ExecutiveSummary }>("/api/v1/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ snapshot, session_id: sessionId }),
  });
  return res.summary;
}

export async function fetchAuditLog(limit = 50): Promise<AuditEvent[]> {
  return request<AuditEvent[]>(`/api/v1/audit?limit=${limit}`);
}

export async function fetchRetentionPolicy(): Promise<RetentionPolicy> {
  return request<RetentionPolicy>("/api/v1/policy/retention");
}

export async function generateForecast(
  monthlyRecords: Record<string, unknown>[],
  metric: string,
  horizonMonths: number
): Promise<ForecastPayload> {
  const res = await request<{ forecast: ForecastPayload }>("/api/v1/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      monthly_records: monthlyRecords,
      metric,
      horizon_months: horizonMonths,
    }),
  });
  return res.forecast;
}

export type ChatMode = "dataset" | "advisory" | "freelance";

export async function sendChat(
  message: string,
  options: {
    sessionId: string;
    history: ChatMessage[];
    mode: ChatMode;
    dashboard?: DashboardData;
    freelanceSummary?: UploadValidation["freelance_summary"];
  }
): Promise<{ answer: string; sources: string[]; chart?: string }> {
  const { sessionId, history, mode, dashboard, freelanceSummary } = options;
  const body: Record<string, unknown> = {
    message,
    session_id: sessionId,
    mode,
    history: history.map((m) => ({ role: m.role, content: m.content })),
    monthly_records: dashboard?.monthly_records ?? [],
    top_expense_categories: dashboard?.top_expense_categories ?? [],
    source_file: dashboard?.source_file ?? "upload",
  };
  if (freelanceSummary) {
    body.freelance_summary = freelanceSummary;
  }
  const res = await request<{
    result: { answer: string; sources: string[]; chart?: string };
  }>("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return res.result;
}

export async function generateExecutiveReport(
  dashboard: DashboardData,
  summary?: ExecutiveSummary | null
): Promise<ReportPayload> {
  return request<ReportPayload>("/api/v1/reports/executive", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      session_id: dashboard.session_id,
      source_file: dashboard.source_file,
      snapshot: dashboard.snapshot,
      monthly_records: dashboard.monthly_records,
      top_expense_categories: dashboard.top_expense_categories,
      anomalies: dashboard.anomalies,
      warnings: dashboard.warnings,
      summary: summary ?? undefined,
    }),
  });
}

export async function fetchWhyPanel(dashboard: DashboardData): Promise<WhyInsight[]> {
  const res = await request<{ insights: WhyInsight[] }>("/api/v1/why-panel", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      monthly_records: dashboard.monthly_records,
      top_expense_categories: dashboard.top_expense_categories,
      anomalies: dashboard.anomalies,
    }),
  });
  return res.insights;
}

export async function checkHealth(): Promise<boolean> {
  try {
    await request<{ status: string }>("/health");
    return true;
  } catch {
    return false;
  }
}

export async function fetchIndustries(): Promise<{ id: string; label: string }[]> {
  return request("/api/v1/benchmarks/industries");
}

export async function fetchAlerts(
  sessionId?: string,
  unreadOnly = false
): Promise<import("@/types/dashboard").AlertItem[]> {
  const params = new URLSearchParams();
  if (sessionId) params.set("session_id", sessionId);
  if (unreadOnly) params.set("unread_only", "true");
  const q = params.toString();
  return request(`/api/v1/alerts${q ? `?${q}` : ""}`);
}

export async function markAlertsRead(sessionId?: string): Promise<void> {
  const q = sessionId ? `?session_id=${sessionId}` : "";
  await request(`/api/v1/alerts/mark-read${q}`, { method: "POST" });
}

export async function runScenario(
  monthlyRecords: Record<string, unknown>[],
  opts: { revenue_delta_pct?: number; opex_delta_pct?: number; cogs_delta_pct?: number }
): Promise<import("@/types/dashboard").ScenarioResult> {
  return request("/api/v1/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      monthly_records: monthlyRecords,
      revenue_delta_pct: opts.revenue_delta_pct ?? 0,
      opex_delta_pct: opts.opex_delta_pct ?? 0,
      cogs_delta_pct: opts.cogs_delta_pct ?? 0,
    }),
  });
}

export async function compareSessions(
  sessionIdA: string,
  sessionIdB: string
): Promise<import("@/types/dashboard").CompareResult> {
  return request("/api/v1/sessions/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ session_id_a: sessionIdA, session_id_b: sessionIdB }),
  });
}

export async function createScheduledReport(body: {
  session_id: string;
  label: string;
  cadence: string;
  format: string;
  recipients: string[];
}): Promise<import("@/types/dashboard").ScheduledReport> {
  return request("/api/v1/scheduled-reports", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
}

export async function listScheduledReports(
  sessionId?: string
): Promise<import("@/types/dashboard").ScheduledReport[]> {
  const q = sessionId ? `?session_id=${sessionId}` : "";
  return request(`/api/v1/scheduled-reports${q}`);
}

export async function runScheduledReport(reportId: number): Promise<{ job_id: string; status: string }> {
  return request(`/api/v1/scheduled-reports/${reportId}/run`, {
    method: "POST",
    headers: authHeaders(),
  });
}

export async function loginUser(body: {
  name: string;
  email: string;
  role: "Admin" | "Analyst";
}): Promise<{ access_token: string; user: DemoUser }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Login failed");
  }
  return res.json();
}

export async function loginGoogle(idToken: string): Promise<{ access_token: string; user: DemoUser }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Google sign-in failed");
  }
  return res.json();
}

export async function fetchAuthConfig(): Promise<{
  google_sso_enabled: boolean;
  jwt_enabled: boolean;
  demo_login_enabled: boolean;
}> {
  return request("/api/v1/auth/config");
}

export async function fetchReadiness(): Promise<{ status: string; checks: Record<string, string> }> {
  return request("/health/ready");
}

export async function enqueueForecastJob(
  monthlyRecords: Record<string, unknown>[],
  metric: string,
  horizonMonths: number
): Promise<{ job_id: string }> {
  return request("/api/v1/jobs/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      monthly_records: monthlyRecords,
      metric,
      horizon_months: horizonMonths,
    }),
  });
}

export async function getJob(jobId: string): Promise<{
  job_id: string;
  status: string;
  result?: Record<string, unknown>;
  error?: string;
}> {
  return request(`/api/v1/jobs/${jobId}`);
}

export async function pollJob<T>(
  jobId: string,
  extract: (result: Record<string, unknown>) => T,
  intervalMs = 1500,
  maxAttempts = 40
): Promise<T> {
  for (let i = 0; i < maxAttempts; i += 1) {
    const job = await getJob(jobId);
    if (job.status === "completed" && job.result) {
      return extract(job.result);
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "Background job failed");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Job timed out");
}

export interface ApiKeyRecord {
  id: number;
  key_prefix: string;
  label: string;
  owner_email: string;
  role: string;
  created_at: string;
  last_used_at?: string | null;
}

export async function listApiKeys(): Promise<ApiKeyRecord[]> {
  return request("/api/v1/admin/api-keys");
}

export async function createApiKey(body: {
  label: string;
  owner_email: string;
  role: "Admin" | "Analyst";
}): Promise<{ raw_key: string; key: ApiKeyRecord }> {
  return request("/api/v1/admin/api-keys", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
}

export async function revokeApiKey(keyId: number): Promise<void> {
  await request(`/api/v1/admin/api-keys/${keyId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export function downloadText(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadBase64Pdf(base64: string, filename: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
