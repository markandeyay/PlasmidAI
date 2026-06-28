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
        cream: "#f7f3ea",
        paper: "#fefcf6",
        // Text
        ink: "#2b2620",
        slate: "#6c6354",
        // Accent (use selectively)
        coral: "#c1553c",
        // Supporting neutrals
        line: "#e3dcc8",
        "line-strong": "#d4caaf",
        mist: "#ece5d4",
        // Semantic validation
        sage: "#6e8a5a",
        honey: "#bd862f",
        clay: "#7e3540",
      },
      fontFamily: {
        serif: [
          "var(--font-serif)",
          "Newsreader",
          "Iowan Old Style",
          "Apple Garamond",
          "Georgia",
          "Times New Roman",
          "serif",
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
        display: ["2.25rem", { lineHeight: "1.2", fontWeight: "600" }],
        h2: ["1.625rem", { lineHeight: "1.25", fontWeight: "600" }],
        h3: ["1.25rem", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["1rem", { lineHeight: "1.6" }],
        small: ["0.875rem", { lineHeight: "1.5" }],
        caption: ["0.75rem", { lineHeight: "1.4", fontWeight: "500" }],
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
        sm: "6px",
        md: "10px",
        lg: "14px",
        pill: "9999px",
      },
      boxShadow: {
        rest: "0 1px 2px rgba(43, 38, 32, 0.06)",
        raised:
          "0 2px 4px rgba(43, 38, 32, 0.07), 0 1px 2px rgba(43, 38, 32, 0.05)",
        floating:
          "0 12px 28px rgba(43, 38, 32, 0.10), 0 4px 10px rgba(43, 38, 32, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;