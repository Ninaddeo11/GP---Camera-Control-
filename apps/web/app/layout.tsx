import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { AuthProvider } from "@/lib/auth-context";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

// The public site and auth pages are branded "GP Sentinel" per the
// landing-page brief; the authenticated app shell (nav-sidebar.tsx,
// top-bar.tsx, etc.) still says "Sentinel Grid" internally — same
// product, and a full rename across the backend, Docker service names,
// and database is a separate, larger piece of work than "build the
// landing page," not folded in here.
export const metadata: Metadata = {
  title: {
    default: "GP Sentinel | Camera Intelligence & Operational Intelligence Platform",
    template: "%s | GP Sentinel",
  },
  description:
    "GP Sentinel transforms distributed camera infrastructure into real-time operational intelligence through AI vision, tracking, ANPR, event intelligence and secure evidence management.",
};

export const viewport: Viewport = {
  themeColor: "#050B12",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
