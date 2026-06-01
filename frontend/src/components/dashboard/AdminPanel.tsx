"use client";

import { useEffect, useState } from "react";
import { Key, Server, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/context/AuthContext";
import {
  createApiKey,
  fetchReadiness,
  listApiKeys,
  revokeApiKey,
  type ApiKeyRecord,
} from "@/lib/api";

export function AdminPanel() {
  const { user } = useAuth();
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [readiness, setReadiness] = useState<{ status: string; checks: Record<string, string> } | null>(
    null
  );
  const [label, setLabel] = useState("");
  const [ownerEmail, setOwnerEmail] = useState(user?.email ?? "");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "Admin") return;
    listApiKeys().then(setKeys).catch(() => setKeys([]));
    fetchReadiness().then(setReadiness).catch(() => setReadiness(null));
  }, [user?.role]);

  if (user?.role !== "Admin") return null;

  const createKey = async () => {
    if (!label.trim() || !ownerEmail.trim()) return;
    setError(null);
    try {
      const res = await createApiKey({
        label: label.trim(),
        owner_email: ownerEmail.trim(),
        role: "Analyst",
      });
      setNewKey(res.raw_key);
      setKeys(await listApiKeys());
      setLabel("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create key");
    }
  };

  const revoke = async (id: number) => {
    await revokeApiKey(id);
    setKeys(await listApiKeys());
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Server className="h-4 w-4 text-accent" />
            System readiness
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {readiness ? (
            <>
              <div className="flex items-center gap-2">
                <span className="text-text-secondary">Status</span>
                <Badge variant={readiness.status === "ready" ? "success" : "warning"}>
                  {readiness.status}
                </Badge>
              </div>
              {Object.entries(readiness.checks).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <span className="text-text-secondary">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </>
          ) : (
            <p className="text-text-secondary">Could not reach /health/ready</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Key className="h-4 w-4 text-accent" />
            API keys (B2B integrations)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-text-secondary">
            Issue keys for programmatic access. Send as{" "}
            <code className="rounded bg-white/5 px-1">X-API-Key</code> header.
          </p>
          <div className="flex flex-wrap gap-2">
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Integration label"
              className="flex-1 rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
            />
            <input
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              placeholder="owner@company.com"
              className="flex-1 rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm"
            />
            <Button onClick={createKey}>Create key</Button>
          </div>
          {newKey && (
            <div className="rounded-xl border border-accent/30 bg-accent/10 p-3 text-xs">
              <p className="font-medium text-text-primary">Copy this key now — it won&apos;t be shown again:</p>
              <code className="mt-2 block break-all text-accent">{newKey}</code>
            </div>
          )}
          {error && <p className="text-xs text-red-300">{error}</p>}
          {keys.length === 0 ? (
            <p className="text-sm text-text-secondary">No API keys yet.</p>
          ) : (
            <ul className="space-y-2">
              {keys.map((k) => (
                <li
                  key={k.id}
                  className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-3 text-sm"
                >
                  <div>
                    <p className="font-medium">{k.label}</p>
                    <p className="text-xs text-text-secondary">
                      {k.key_prefix}… · {k.owner_email} · {k.role}
                    </p>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => revoke(k.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
