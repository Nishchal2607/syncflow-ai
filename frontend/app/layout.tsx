import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SyncFlow AI",
  description: "A human-steerable AI agent collaboration platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-slate-100 antialiased">{children}</body>
    </html>
  );
}
