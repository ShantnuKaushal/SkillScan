import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SkillScan",
  description: "Job search and skill graph exploration."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
