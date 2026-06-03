import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        panel: "#f6f8f4",
        line: "#d8dfd7",
        action: "#1f7a6d",
        warning: "#b35c00"
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(23, 32, 38, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
