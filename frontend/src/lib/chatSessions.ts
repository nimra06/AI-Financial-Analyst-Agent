/** Client-side chat keys that are not persisted as dataset workspaces. */
export const EPHEMERAL_CHAT_SESSIONS = new Set(["advisory", "advisory-freelance"]);

export function isEphemeralChatSession(sessionId: string | null | undefined): boolean {
  if (!sessionId) return true;
  return EPHEMERAL_CHAT_SESSIONS.has(sessionId);
}
