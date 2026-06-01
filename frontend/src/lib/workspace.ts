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
