"use client";

import { ArchitectureSection } from "./architecture-section";
import { CapabilitiesSection } from "./capabilities-section";
import { CtaSection } from "./cta-section";
import { EventIntelligenceSection } from "./event-intelligence-section";
import { LandingFooter } from "./footer";
import { FrameToIntelligenceSection } from "./frame-to-intelligence-section";
import { Hero } from "./hero";
import { LivingNetworkSection } from "./living-network-section";
import { LandingNav } from "./nav";
import { PipelineSection } from "./pipeline-section";
import { RolesSection } from "./roles-section";
import { SearchDemoSection } from "./search-demo-section";
import { SecuritySection } from "./security-section";
import { TelemetryStrip } from "./telemetry-strip";

/**
 * The public "/" experience — see README.md "Design mandate" for why this
 * intentionally uses a different, more cinematic palette than the
 * authenticated app shell (.landing-page in app/globals.css). Composed as
 * one client component (rather than each section importing "use client"
 * independently at the page level) so app/page.tsx itself can stay a
 * server component and export SEO metadata, which a "use client" page
 * cannot do.
 */
export function LandingPage() {
  return (
    <div className="landing-page min-h-screen overflow-x-hidden">
      <LandingNav />
      <Hero />
      <TelemetryStrip />
      <PipelineSection />
      <CapabilitiesSection />
      <FrameToIntelligenceSection />
      <LivingNetworkSection />
      <EventIntelligenceSection />
      <RolesSection />
      <SecuritySection />
      <ArchitectureSection />
      <SearchDemoSection />
      <CtaSection />
      <LandingFooter />
    </div>
  );
}
