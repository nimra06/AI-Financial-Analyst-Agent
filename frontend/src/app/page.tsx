"use client";

import { useEffect } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { DisclaimerBanner } from "@/components/layout/DisclaimerBanner";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { FloatingChat } from "@/components/dashboard/FloatingChat";
import { DemoSignIn } from "@/components/auth/DemoSignIn";
import { checkHealth } from "@/lib/api";

export default function HomePage() {
  useEffect(() => {
    checkHealth().then((ok) => {
      if (!ok) console.warn("API offline — start FastAPI on port 8000");
    });
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <DisclaimerBanner />
        <main className="flex-1 overflow-y-auto p-8 pb-24">
          <DashboardView />
        </main>
      </div>
      <FloatingChat />
      <DemoSignIn />
    </div>
  );
}
