"use client";

import { AnprSection } from "./anpr-section";
import { CameraUnderstandsSection } from "./camera-understands-section";
import { CapabilitiesSection } from "./capabilities-section";
import { CtaSection } from "./cta-section";
import { EventCorrelationSection } from "./event-correlation-section";
import { LandingFooter } from "./footer";
import { FrameToIntelligenceSection } from "./frame-to-intelligence-section";
import { Hero } from "./hero";
import { LivingNetworkSection } from "./living-network-section";
import { MultiCameraSection } from "./multi-camera-section";
import { LandingNav } from "./nav";
import { PipelineWordsSection } from "./pipeline-words-section";
import { RolesSection } from "./roles-section";
import { ScrollCameraExperienceSection } from "./scroll-camera-experience-section";
import { SecuritySection } from "./security-section";
import { TransitionStrip } from "./transition-strip";

/**
 * The public "/" experience — see README.md "Design mandate" for why this
 * intentionally uses a different, more cinematic palette than the
 * authenticated app shell (.landing-page in app/globals.css). Composed as
 * one client component (rather than each section importing "use client"
 * independently at the page level) so app/page.tsx itself can stay a
 * server component and export SEO metadata, which a "use client" page
 * cannot do.
 *
 * Section order follows the V2 brief's narrative arc: a camera seeing, to
 * a camera understanding, to a platform that operates on that
 * understanding — rather than the V1 structure of stats-then-features.
 */
export function LandingPage() {
  return (
    <div className="landing-page min-h-screen overflow-x-hidden">
      <LandingNav />
      <Hero />
      <TransitionStrip />
      <CameraUnderstandsSection />
      <FrameToIntelligenceSection />
      <ScrollCameraExperienceSection />
      <PipelineWordsSection />
      <MultiCameraSection />
      <AnprSection />
      <EventCorrelationSection />
      <LivingNetworkSection />
      <CapabilitiesSection />
      <RolesSection />
      <SecuritySection />
      <CtaSection />
      <LandingFooter />
    </div>
  );
}
