"use client";

import { useEffect, useRef, useState } from "react";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { roleLabel } from "@/lib/permissions";
import { GOOGLE_CLIENT_ID, type DemoUser } from "@/lib/auth";
import { fetchAuthConfig } from "@/lib/api";

const ROLES: DemoUser["role"][] = ["Analyst", "Admin"];

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (cfg: {
            client_id: string;
            callback: (resp: { credential: string }) => void;
          }) => void;
          renderButton: (
            el: HTMLElement,
            opts: { theme?: string; size?: string; width?: number }
          ) => void;
        };
      };
    };
  }
}

export function DemoSignIn() {
  const { user, ready, signIn, signInGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<DemoUser["role"]>("Analyst");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const googleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAuthConfig()
      .then((cfg) => setGoogleEnabled(cfg.google_sso_enabled && !!GOOGLE_CLIENT_ID))
      .catch(() => setGoogleEnabled(false));
  }, []);

  useEffect(() => {
    if (!googleEnabled || !googleRef.current || !GOOGLE_CLIENT_ID) return;

    const init = () => {
      if (!window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (resp) => {
          setLoading(true);
          setError(null);
          try {
            await signInGoogle(resp.credential);
          } catch (e) {
            setError(e instanceof Error ? e.message : "Google sign-in failed");
          } finally {
            setLoading(false);
          }
        },
      });
      if (googleRef.current) {
        window.google.accounts.id.renderButton(googleRef.current, {
          theme: "outline",
          size: "large",
          width: 320,
        });
      }
    };

    if (window.google?.accounts?.id) {
      init();
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = init;
    document.body.appendChild(script);
    return () => {
      script.remove();
    };
  }, [googleEnabled, signInGoogle]);

  if (!ready || user) return null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await signIn(name, email, role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-md border-white/10 shadow-2xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/20 ring-1 ring-accent/30">
            <LogIn className="h-6 w-6 text-accent" />
          </div>
          <CardTitle>Sign in to FinAnalyst AI</CardTitle>
          <p className="text-sm text-text-secondary">
            JWT-secured workspace · role-based access
          </p>
        </CardHeader>
        <CardContent>
          {googleEnabled && (
            <div className="mb-4 flex flex-col items-center gap-2">
              <div ref={googleRef} />
              <p className="text-xs text-text-secondary">or continue with email</p>
            </div>
          )}
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Full name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Morgan"
                className="w-full rounded-xl border border-white/10 bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30"
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Work email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alex@company.com"
                className="w-full rounded-xl border border-white/10 bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30"
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`rounded-xl border px-2 py-2 text-xs font-medium transition ${
                      role === r
                        ? "border-accent bg-accent/15 text-text-primary"
                        : "border-white/10 text-text-secondary hover:border-white/20"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
              <p className="mt-1.5 text-[11px] text-text-secondary">{roleLabel(role)}</p>
            </div>
            {error && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in…" : "Enter workspace"}
            </Button>
            <p className="text-center text-[11px] text-text-secondary">
              Demo only · Not financial advice · Data stays on your machine
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
