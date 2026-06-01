import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B0F19",
        surface: "#111827",
        card: "#1F2937",
        accent: "#3B82F6",
        "text-primary": "#E5E7EB",
        "text-secondary": "#9CA3AF",
        success: "#10B981",
        warning: "#F59E0B",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 24px rgba(0, 0, 0, 0.35)",
        glow: "0 0 0 1px rgba(59, 130, 246, 0.15), 0 8px 32px rgba(0, 0, 0, 0.4)",
      },
      borderRadius: {
        xl: "12px",
        "2xl": "16px",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.35s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
