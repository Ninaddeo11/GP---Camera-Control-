"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";

import { HeroCityBackground } from "./hero-city-background";
import { HeroIntelligenceOverlay, STORY_PHASE_COUNT, STORY_PHASE_DURATION_MS } from "./hero-intelligence-overlay";

// Maps the shared story-phase counter to which camera node the background
// highlights — kept here (not inside hero-city-background.tsx) so the one
// timeline in this file is the single source of truth for pacing across
// both the background and the overlay panels; see their own comments for
// what each phase does.
function nodeIndexForPhase(phase: number): number {
  if (phase <= 0) return -1;
  if (phase === 1) return 0;
  if (phase <= 3) return 1;
  if (phase <= 5) return 2;
  return -1;
}

// The representative "fully assembled" frame shown, frozen, under
// prefers-reduced-motion — not an empty ambient hero, and not the
// briefly-shown alert state either, since that's the exceptional case,
// not the default one.
const REDUCED_MOTION_PHASE = 4;

export function Hero() {
  const { user } = useAuth();
  const prefersReducedMotion = useReducedMotion();
  const [phase, setPhase] = useState(0);

  // One continuous 8-12s narrative loop (brief section 16): city/cameras
  // -> vehicle moves -> detection -> tracking -> plate recognition ->
  // watchlist alert -> back to ambient. Looping, not a one-shot intro,
  // so it reads as "a living system" rather than a loading animation.
  useEffect(() => {
    if (prefersReducedMotion) return;
    const id = setInterval(() => {
      setPhase((p) => (p + 1) % STORY_PHASE_COUNT);
    }, STORY_PHASE_DURATION_MS);
    return () => clearInterval(id);
  }, [prefersReducedMotion]);

  const effectivePhase = prefersReducedMotion ? REDUCED_MOTION_PHASE : phase;

  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden bg-lp-bg-00 pt-24">
      <HeroCityBackground activeNodeIndex={nodeIndexForPhase(effectivePhase)} />
      <HeroIntelligenceOverlay phase={effectivePhase} />

      <div className="relative z-20 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-[560px]">
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-6 text-xs font-semibold uppercase tracking-[0.25em] text-lp-secondary"
          >
            Safer Cities. Smarter Tomorrow.
          </motion.p>

          {/* Elegant clip-path/blur line reveal, not a typewriter effect
              (brief section 32/34). */}
          <h1 className="text-4xl font-bold leading-[1.08] tracking-tight text-lp-text-0 sm:text-5xl lg:text-6xl">
            <RevealLine delay={0.05}>SEE THE SIGNAL.</RevealLine>
            <RevealLine delay={0.2}>
              <span className="text-lp-primary-2">UNDERSTAND</span>
            </RevealLine>
            <RevealLine delay={0.35}>
              <span className="text-lp-primary-2">THE MOVEMENT.</span>
            </RevealLine>
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.5 }}
            className="mt-7 max-w-[520px] text-[17px] leading-relaxed text-lp-text-1 sm:text-lg"
          >
            GP Sentinel transforms camera data into actionable intelligence —
            helping organizations understand movement, events and activity
            through one intelligent platform.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.62 }}
            className="mt-9 flex flex-col items-start gap-4 sm:flex-row sm:items-center"
          >
            <Link
              href={user ? "/trace" : "/login"}
              className="group inline-flex items-center gap-2 rounded-md bg-lp-primary px-6 py-3 text-sm font-semibold uppercase tracking-wider text-white shadow-[0_0_32px_-8px_rgba(22,136,255,0.6)] transition-all hover:bg-lp-primary-2 hover:shadow-[0_0_40px_-6px_rgba(46,168,255,0.75)]"
            >
              Enter GP Sentinel
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
            <a
              href="#intelligence"
              className="inline-flex items-center gap-2 rounded-md border border-lp-border bg-lp-bg-0/40 px-6 py-3 text-sm font-semibold uppercase tracking-wider text-lp-text-1 backdrop-blur-sm transition-colors hover:border-lp-primary/50 hover:text-lp-text-0"
            >
              <span aria-hidden="true" className="text-lp-primary-2">
                ◉
              </span>
              Explore the Platform
            </a>
          </motion.div>
        </div>
      </div>

      <div className="absolute bottom-7 left-4 z-20 flex items-center gap-2.5 text-lp-text-2 sm:left-6 lg:left-8">
        <motion.svg
          width="16"
          height="24"
          viewBox="0 0 16 24"
          fill="none"
          aria-hidden="true"
          className="shrink-0"
        >
          <rect x="1" y="1" width="14" height="22" rx="7" stroke="currentColor" strokeWidth="1.5" />
          <motion.circle
            cx="8"
            r="2"
            fill="currentColor"
            initial={{ cy: 7 }}
            animate={prefersReducedMotion ? { cy: 7 } : { cy: [7, 13, 7] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.svg>
        <span className="text-[10px] font-semibold uppercase tracking-[0.2em]">Scroll to Explore</span>
      </div>

      <div className="absolute bottom-7 right-4 z-20 hidden text-right text-[10px] font-semibold uppercase tracking-[0.2em] text-lp-text-2 sm:block sm:right-6 lg:right-8">
        Real Movement. Real Context. Safer Communities.
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-32 bg-gradient-to-t from-lp-bg-0 to-transparent" />
    </section>
  );
}

function RevealLine({ children, delay }: { children: React.ReactNode; delay: number }) {
  return (
    <span className="block overflow-hidden">
      <motion.span
        initial={{ y: "110%", opacity: 0, filter: "blur(6px)" }}
        animate={{ y: "0%", opacity: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
        className="block"
      >
        {children}
      </motion.span>
    </span>
  );
}
