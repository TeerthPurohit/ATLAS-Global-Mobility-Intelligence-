import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          0: "var(--surface-0)",
          1: "var(--surface-1)",
          2: "var(--surface-2)",
          border: "var(--surface-border)",
        },
        ink: {
          primary: "var(--ink-primary)",
          secondary: "var(--ink-secondary)",
          muted: "var(--ink-muted)",
        },
        parchment: "var(--parchment)",
        brass: {
          DEFAULT: "var(--brass)",
          fg: "var(--brass-fg)",
        },
        verdigris: "var(--verdigris)",
        oxide: "var(--oxide)",
        accent: {
          DEFAULT: "var(--accent)",
          fg: "var(--accent-fg)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "SFMono-Regular", "monospace"],
      },
      keyframes: {
        "border-beam": {
          "100%": {
            "offset-distance": "100%",
          },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        spotlight: {
          "0%": { opacity: "0", transform: "translate(-50%, -50%) scale(0.8)" },
          "100%": { opacity: "1", transform: "translate(-50%, -50%) scale(1)" },
        },
      },
      animation: {
        "border-beam": "border-beam var(--duration) infinite linear",
        shimmer: "shimmer 2.5s infinite linear",
        spotlight: "spotlight 0.5s ease-out forwards",
      },
    },
  },
  plugins: [],
};
export default config;
