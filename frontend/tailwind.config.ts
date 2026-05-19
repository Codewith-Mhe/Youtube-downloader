import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070708",
          900: "#0d0d10",
          800: "#16161b",
          700: "#1f1f26",
          600: "#2a2a33",
          500: "#3a3a45",
        },
        bone: "#f4f1ea",
        chalk: "#e8e4d9",
        lime: {
          DEFAULT: "#c8f25c",
          bright: "#d6ff5e",
          deep: "#9fbf3a",
        },
        coral: "#ff7a59",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-instrument-serif)", "Georgia", "serif"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        "grain": "grain 8s steps(10) infinite",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        grain: {
          "0%, 100%": { transform: "translate(0, 0)" },
          "10%": { transform: "translate(-2%, -2%)" },
          "30%": { transform: "translate(2%, -1%)" },
          "50%": { transform: "translate(-1%, 2%)" },
          "70%": { transform: "translate(1%, 1%)" },
          "90%": { transform: "translate(-2%, 1%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
