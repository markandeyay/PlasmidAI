import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PlasmidAI",
  description: "Natural-language plasmid design workspace"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
