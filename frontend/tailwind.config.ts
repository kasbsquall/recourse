import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Agent palette classes (bg-blue-50, border-purple-200, etc.) are written as
  // full string literals in the AGENTS map, so Tailwind's content scan finds them.
  // Safelisting the families keeps them even if a class is composed dynamically.
  safelist: [
    {
      pattern:
        /(bg|text|border)-(blue|purple|red|green|yellow|cyan|gray)-(50|100|200|600|800)/,
    },
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
