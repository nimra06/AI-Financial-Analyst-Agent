import type { Metadata } from "next";
import "./globals.css";
import { DashboardProvider } from "@/context/DashboardContext";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "FinAnalyst AI | Enterprise Financial Intelligence",
  description: "AI-powered financial analyst dashboard for modern finance teams",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased">
        <AuthProvider>
          <DashboardProvider>{children}</DashboardProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
