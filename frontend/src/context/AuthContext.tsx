"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  clearAuthSession,
  persistAccessToken,
  persistDemoUser,
  readAccessToken,
  readDemoUser,
  type DemoUser,
} from "@/lib/auth";
import { loginGoogle, loginUser } from "@/lib/api";

interface AuthContextValue {
  user: DemoUser | null;
  ready: boolean;
  signIn: (name: string, email: string, role?: DemoUser["role"]) => Promise<void>;
  signInGoogle: (idToken: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = readDemoUser();
    const token = readAccessToken();
    if (stored && token) {
      setUser(stored);
    } else if (stored && !token) {
      clearAuthSession();
      setUser(null);
    }
    setReady(true);

    const onExpired = () => setUser(null);
    window.addEventListener("finanalyst:session-expired", onExpired);
    return () => window.removeEventListener("finanalyst:session-expired", onExpired);
  }, []);

  const signIn = useCallback(
    async (name: string, email: string, role: DemoUser["role"] = "Analyst") => {
      const res = await loginUser({ name: name.trim(), email: email.trim(), role });
      const next: DemoUser = {
        name: res.user.name,
        email: res.user.email,
        role: res.user.role as DemoUser["role"],
      };
      persistAccessToken(res.access_token);
      persistDemoUser(next);
      setUser(next);
    },
    []
  );

  const signInGoogle = useCallback(async (idToken: string) => {
    const res = await loginGoogle(idToken);
    const next: DemoUser = {
      name: res.user.name,
      email: res.user.email,
      role: (res.user.role as DemoUser["role"]) ?? "Analyst",
    };
    persistAccessToken(res.access_token);
    persistDemoUser(next);
    setUser(next);
  }, []);

  const signOut = useCallback(() => {
    clearAuthSession();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, ready, signIn, signInGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
