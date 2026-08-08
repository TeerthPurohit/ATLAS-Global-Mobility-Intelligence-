import type { Config } from "tailwindcss";

// Design tokens: navigational-instrument palette (chart-table dark surfaces,
// brass = "computed"/certain, verdigris = "modeled_estimate", oxide =
// "unavailable" -- see basis system in lib/api.ts). `accent` is kept as an
// alias for `brass` since Button/Input/Select/NavBar already reference it.
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
    },
  },
  plugins: [],
};
export default config;
