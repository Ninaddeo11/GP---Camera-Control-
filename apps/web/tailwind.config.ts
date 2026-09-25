import type { Config } from "tailwindcss";

// Design mandate: navy/slate/white base, one accent color, no neon/glow —
// see README.md "Design mandate". Colors are CSS variables (app/globals.css)
// so light/dark mode both stay professional slate, not black-and-neon.
const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--background) / <alpha-value>)",
        foreground: "rgb(var(--foreground) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-muted": "rgb(var(--surface-muted) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        "accent-foreground": "rgb(var(--accent-foreground) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)",
        warning: "rgb(var(--warning) / <alpha-value>)",
        success: "rgb(var(--success) / <alpha-value>)",

        // Public landing page only — see app/globals.css's .landing-page
        // block. "lp-" prefixed so these never get reached for by mistake
        // inside the authenticated app shell.
        "lp-bg-0": "rgb(var(--lp-bg-0) / <alpha-value>)",
        "lp-bg-1": "rgb(var(--lp-bg-1) / <alpha-value>)",
        "lp-bg-2": "rgb(var(--lp-bg-2) / <alpha-value>)",
        "lp-primary": "rgb(var(--lp-primary) / <alpha-value>)",
        "lp-primary-2": "rgb(var(--lp-primary-2) / <alpha-value>)",
        "lp-secondary": "rgb(var(--lp-secondary) / <alpha-value>)",
        "lp-success": "rgb(var(--lp-success) / <alpha-value>)",
        "lp-warning": "rgb(var(--lp-warning) / <alpha-value>)",
        "lp-alert": "rgb(var(--lp-alert) / <alpha-value>)",
        "lp-text-0": "rgb(var(--lp-text-0) / <alpha-value>)",
        "lp-text-1": "rgb(var(--lp-text-1) / <alpha-value>)",
        "lp-text-2": "rgb(var(--lp-text-2) / <alpha-value>)",
        "lp-border": "rgb(var(--lp-border) / <alpha-value>)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      borderRadius: {
        DEFAULT: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
