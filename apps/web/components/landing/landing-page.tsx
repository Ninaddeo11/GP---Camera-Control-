"use client";

import { CapabilitiesSection } from "./capabilities-section";
import { CameraUnderstandsSection } from "./camera-understands-section";
import { CtaSection } from "./cta-section";
import { EventCorrelationSection } from "./event-correlation-section";
import { LandingFooter } from "./footer";
import { Hero } from "./hero";
import { MultiCameraSection } from "./multi-camera-section";
import { LandingNav } from "./nav";
import { RolesSection } from "./roles-section";
import { ScrollCameraExperienceSection } from "./scroll-camera-experience-section";
import { SecuritySection } from "./security-section";

/**
 * The public "/" experience — see README.md "Design mandate" for why this
 * intentionally uses a different, more cinematic palette than the
 * authenticated app shell (.landing-page in app/globals.css). Composed as
 * one client component (rather than each section importing "use client"
 * independently at the page level) so app/page.tsx itself can stay a
 * server component and export SEO metadata, which a "use client" page
 * cannot do.
 *
 * Section order follows the "exact redesign" brief's leaner structure —
 * real city photography carrying the hero, then a tight sequence of
 * purposeful sections rather than the earlier, more numerous abstract-
 * network-based sections. See each component's own docstring for what it
 * replaced and why.
 */
export function LandingPage() {
  return (
    // No overflow-x-hidden here: it forces `overflow-y: auto` on this div
    // too (per the CSS overflow spec, a non-visible x with a visible y
    // computes the y to auto), which makes THIS div the sticky containing
    // block for every descendant instead of the viewport — silently
    // breaking position:sticky for scroll-camera-experience-section.tsx's
    // 600vh sticky sequence (confirmed by screenshotting it: the section
    // rendered completely blank once scrolled into). Any section that
    // needs horizontal clipping (e.g. a parallax layer sliding past its
    // edge) scopes its own `overflow-hidden` locally instead — see
    // hero-city-background.tsx.
    <div className="landing-page min-h-screen">
      <LandingNav />
      <Hero />
      <CameraUnderstandsSection />
      <ScrollCameraExperienceSection />
      <MultiCameraSection />
      <EventCorrelationSection />
      <CapabilitiesSection />
      <RolesSection />
      <SecuritySection />
      <CtaSection />
      <LandingFooter />
    </div>
  );
}
