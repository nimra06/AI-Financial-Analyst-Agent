/** Auth session — JWT + demo user profile (localStorage). */

export const DEMO_USER_KEY = "finanalyst_demo_user";
export const AUTH_TOKEN_KEY = "finanalyst_access_token";

export interface DemoUser {
  name: string;
  email: string;
  role: "Admin" | "Analyst";
}

export function readDemoUser(): DemoUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(DEMO_USER_KEY);
    return raw ? (JSON.parse(raw) as DemoUser) : null;
  } catch {
    return null;
  }
}

export function persistDemoUser(user: DemoUser): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(DEMO_USER_KEY, JSON.stringify(user));
}

export function clearDemoUser(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(DEMO_USER_KEY);
}

export function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function persistAccessToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function clearAuthSession(): void {
  clearDemoUser();
  clearAccessToken();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("finanalyst:session-expired"));
  }
}

export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
