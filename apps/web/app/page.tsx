import type { Metadata } from "next";

import { LandingPage } from "@/components/landing/landing-page";

export const metadata: Metadata = {
  title: "GP Sentinel | Camera Intelligence & Operational Intelligence Platform",
  description:
    "GP Sentinel transforms distributed camera infrastructure into real-time operational intelligence through AI vision, tracking, ANPR, event intelligence and secure evidence management.",
  openGraph: {
    title: "GP Sentinel | Camera Intelligence & Operational Intelligence Platform",
    description:
      "GP Sentinel transforms distributed camera infrastructure into real-time operational intelligence through AI vision, tracking, ANPR, event intelligence and secure evidence management.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "GP Sentinel | Camera Intelligence & Operational Intelligence Platform",
    description:
      "GP Sentinel transforms distributed camera infrastructure into real-time operational intelligence.",
  },
};

export default function RootPage() {
  return <LandingPage />;
}
