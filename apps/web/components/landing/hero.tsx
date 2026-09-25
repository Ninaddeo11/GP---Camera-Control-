"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";

import { HeroNetworkBackground, STORY_NODES } from "./hero-network-background";
import { HeroStoryOverlay } from "./hero-story-overlay";

const STORY_INTERVAL_MS = 4200;

export function Hero() {
  const { user } = useAuth();
  const prefersReducedMotion = useReducedMotion();
  const [storyPhase, setStoryPhase] = useState(0);

  // A continuous, looping ambient narrative (network forms -> a vehicle is
  // detected -> tracked -> recognized -> its event correlates across
  // cameras -> repeat) rather than a literal one-shot, hand-choreographed
  // 9-phase cutscene — this drives both the SVG background's highlighted
  // node/correlation lines and the floating caption card off one shared
  // index, so they can never drift out of sync, and it degrades to a
  // single static frame under prefers-reduced-motion instead of cycling.
  useEffect(() => {
    if (prefersReducedMotion) return;
    const id = setInterval(() => {
      setStoryPhase((p) => (p + 1) % STORY_NODES.length);
    }, STORY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [prefersReducedMotion]);

  return (
    <section className="relative flex min-h-screen items-center overflow-hidden bg-lp-bg-00 pt-24">
      <HeroNetworkBackground storyPhase={storyPhase} />
      <HeroStoryOverlay storyPhase={storyPhase} />

      <div className="relative z-10 mx-auto w-full max-w-5xl px-4 text-center sm:px-6 lg:px-8">
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-6 text-xs font-semibold uppercase tracking-[0.3em] text-lp-secondary"
        >
          Operational Intelligence Platform
        </motion.p>

        {/* Line-by-line reveal via clip-path + translateY (brief section
            34) — not a typewriter effect. */}
        <h1 className="text-4xl font-bold leading-[1.05] tracking-tight text-lp-text-0 sm:text-6xl lg:text-7xl">
          <RevealLine delay={0.05}>SEE THE SIGNAL.</RevealLine>
          <RevealLine delay={0.22}>
            <span className="bg-gradient-to-r from-lp-primary-2 to-lp-tertiary bg-clip-text text-transparent">
              UNDERSTAND THE MOVEMENT.
            </span>
          </RevealLine>
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="mx-auto mt-7 max-w-2xl text-base leading-relaxed text-lp-text-1 sm:text-lg"
        >
          GP Sentinel transforms camera data into actionable intelligence — helping
          organizations understand movement, events and activity through one
          intelligent platform.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.55 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <Link
            href={user ? "/trace" : "/login"}
            className="group inline-flex items-center gap-2 rounded bg-lp-primary px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-white shadow-[0_0_40px_-8px_rgba(22,136,255,0.6)] transition-all hover:bg-lp-primary-2 hover:shadow-[0_0_50px_-6px_rgba(46,168,255,0.75)]"
          >
            Enter GP Sentinel
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
          <a
            href="#capabilities"
            className="rounded border border-lp-border px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-lp-text-1 transition-colors hover:border-lp-primary/50 hover:text-lp-text-0"
          >
            Explore the Platform
          </a>
        </motion.div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-lp-bg-0 to-transparent" />
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
