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
        // Surfaces
        cream: "#fbfbf8",
        paper: "#fffffc",
        // Text
        ink: "#1f2320",
        slate: "#5f665f",
        // Accent (use selectively). Token name retained for cascade compatibility.
        coral: "#365f43",
        // Supporting neutrals
        line: "#e3e3dc",
        "line-strong": "#c9cbc2",
        mist: "#f0f1ec",
        // Semantic validation
        sage: "#6f7f68",
        honey: "#a9782c",
        clay: "#7b3d45",
      },
      fontFamily: {
        serif: [
          "var(--font-serif)",
          "Inter Tight",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        sans: [
          "var(--font-sans)",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      fontSize: {
        display: ["2.25rem", { lineHeight: "1.1", fontWeight: "650", letterSpacing: "-0.035em" }],
        h2: ["1.625rem", { lineHeight: "1.15", fontWeight: "650", letterSpacing: "-0.03em" }],
        h3: ["1.25rem", { lineHeight: "1.2", fontWeight: "650", letterSpacing: "-0.025em" }],
        body: ["1rem", { lineHeight: "1.5" }],
        small: ["0.875rem", { lineHeight: "1.43" }],
        caption: ["0.75rem", { lineHeight: "1.3", fontWeight: "550" }],
      },
      spacing: {
        "2xs": "4px",
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "48px",
        "3xl": "64px",
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        pill: "9999px",
      },
      boxShadow: {
        rest: "0 1px 2px rgba(31, 35, 32, 0.04)",
        raised:
          "0 2px 4px rgba(31, 35, 32, 0.05), 0 1px 1px rgba(31, 35, 32, 0.04)",
        floating:
          "0 12px 24px rgba(31, 35, 32, 0.08), 0 2px 6px rgba(31, 35, 32, 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
