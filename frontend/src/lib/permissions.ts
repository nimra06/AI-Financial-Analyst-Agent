import type { DemoUser } from "@/lib/auth";

export function canWrite(user: DemoUser | null): boolean {
  if (!user) return false;
  return user.role === "Analyst" || user.role === "Admin";
}

export function canViewAudit(user: DemoUser | null): boolean {
  if (!user) return false;
  return user.role === "Analyst" || user.role === "Admin";
}

export function roleLabel(role: DemoUser["role"]): string {
  switch (role) {
    case "Admin":
      return "Full access + audit";
    case "Analyst":
      return "Upload, AI, exports";
    case "Viewer":
      return "Read-only dashboards";
  }
}
