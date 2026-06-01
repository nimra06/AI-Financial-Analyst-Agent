/** Persists the user's active financial dataset across page reloads. */
export const ACTIVE_SESSION_KEY = "finanalyst_active_session_id";

export function persistActiveSession(sessionId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
}

export function readActiveSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_SESSION_KEY);
}

export function clearActiveSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACTIVE_SESSION_KEY);
}

const FREELANCE_VALIDATION_KEY = "finanalyst_freelance_validation";

export function persistFreelanceValidation(validation: {
  errors: string[];
  warnings: string[];
  row_count: number;
  detected_format?: string | null;
  freelance_insights?: string[];
  freelance_summary?: unknown;
}): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(FREELANCE_VALIDATION_KEY, JSON.stringify(validation));
}

export function readFreelanceValidation(): import("@/types/dashboard").UploadValidation | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(FREELANCE_VALIDATION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as import("@/types/dashboard").UploadValidation;
  } catch {
    return null;
  }
}

export function clearFreelanceValidation(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(FREELANCE_VALIDATION_KEY);
}
