import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { DashboardProvider } from "@/context/DashboardContext";
import { AuthProvider } from "@/context/AuthContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

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
      <body className={`${inter.variable} font-sans`}>
        <AuthProvider>
          <DashboardProvider>{children}</DashboardProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
