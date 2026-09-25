"use client";

import {
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from "framer-motion";
import { useRef, useState } from "react";

const STAGES = ["A Moment", "Detected", "Tracked", "Recognized", "Connected", "Understood"] as const;

interface StageWindow {
  fadeInStart: number;
  fullyIn: number;
  fadeOutStart: number;
  fadeOutEnd: number;
}

function windowFor(index: number, total: number): StageWindow {
  const span = 1 / total;
  const start = index * span;
  return {
    fadeInStart: Math.max(0, start - span * 0.15),
    fullyIn: start + span * 0.15,
    fadeOutStart: start + span * 0.85,
    fadeOutEnd: Math.min(1, start + span * 1.15),
  };
}

/**
 * A sticky, scroll-scrubbed sequence (brief section 13) — six progressively
 * richer states of the same demo camera scene, driven directly by scroll
 * position within a tall container rather than a fixed-duration animation.
 * Falls back to a simple stacked reveal (no sticky pin, no scroll-scrub)
 * under prefers-reduced-motion, since pinning the viewport for several
 * scroll-lengths is itself a strong motion effect some users want to avoid.
 */
export function ScrollCameraExperienceSection() {
  const prefersReducedMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start start", "end end"] });
  const [activeLabel, setActiveLabel] = useState<string>(STAGES[0]);

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const idx = Math.min(STAGES.length - 1, Math.floor(v * STAGES.length));
    setActiveLabel(STAGES[idx] ?? STAGES[0]);
  });

  if (prefersReducedMotion) {
    return (
      <section className="py-24 sm:py-28">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <ol className="space-y-6">
            {STAGES.map((stage, i) => (
              <li key={stage} className="flex items-center gap-4 rounded border border-lp-border bg-lp-bg-1/50 p-5">
                <span className="font-mono text-xs text-lp-primary-2">0{i + 1}</span>
                <span className="text-sm font-semibold uppercase tracking-wider text-lp-text-0">{stage}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>
    );
  }

  return (
    <section ref={containerRef} className="relative h-[600vh]">
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div className="relative aspect-[4/3] overflow-hidden rounded border border-lp-border bg-lp-bg-0">
            {STAGES.map((_, i) => (
              <StageVisual key={i} stage={i} scrollYProgress={scrollYProgress} total={STAGES.length} />
            ))}
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-lp-text-2">
              Scroll to follow one vehicle
            </p>
            <motion.h2
              key={activeLabel}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-4 text-4xl font-bold uppercase tracking-tight text-lp-primary-2 sm:text-6xl"
            >
              {activeLabel}
            </motion.h2>
            <div className="mt-8 flex gap-1.5">
              {STAGES.map((stage, i) => (
                <span
                  key={stage}
                  className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                    STAGES.indexOf(activeLabel as (typeof STAGES)[number]) >= i ? "bg-lp-primary-2" : "bg-lp-border"
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function StageVisual({
  stage,
  scrollYProgress,
  total,
}: {
  stage: number;
  scrollYProgress: MotionValue<number>;
  total: number;
}) {
  const w = windowFor(stage, total);
  const opacity = useTransform(
    scrollYProgress,
    [w.fadeInStart, w.fullyIn, w.fadeOutStart, w.fadeOutEnd],
    [0, 1, 1, 0]
  );

  return (
    <motion.div style={{ opacity }} className="absolute inset-0">
      <svg viewBox="0 0 400 300" className="h-full w-full" aria-hidden="true">
        <defs>
          <linearGradient id={`scene-sky-${stage}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0B1624" />
            <stop offset="100%" stopColor="#03070D" />
          </linearGradient>
        </defs>
        <rect width="400" height="300" fill={`url(#scene-sky-${stage})`} />
        <path d="M0 220 L160 120 L240 120 L400 220 Z" fill="#0B1624" opacity="0.7" />
        <path d="M160 300 L180 130 L220 130 L240 300 Z" fill="#07111C" />

        {/* Stage 1+: bounding box */}
        {stage >= 1 && (
          <rect x="182" y="150" width="36" height="46" rx="2" fill="none" stroke="#FF4D5A" strokeWidth="1.5" />
        )}

        {/* Stage 2+: movement trail */}
        {stage >= 2 && (
          <path
            d="M200 196 C 195 220, 190 240, 185 260"
            fill="none"
            stroke="#57BCFF"
            strokeWidth="1.5"
            strokeDasharray="3 4"
          />
        )}

        {/* Stage 3+: identity card */}
        {stage >= 3 && (
          <g>
            <rect x="240" y="140" width="120" height="46" rx="3" fill="#07111C" stroke="#1688FF" strokeOpacity="0.5" />
            <text x="250" y="158" fill="#94A3B8" fontSize="8" fontFamily="monospace">
              IDENTITY SIGNAL
            </text>
            <text x="250" y="174" fill="#FFFFFF" fontSize="10" fontFamily="monospace">
              MH12AB1234
            </text>
          </g>
        )}

        {/* Stage 4+: connected cameras */}
        {stage >= 4 && (
          <g stroke="#2EA8FF" strokeOpacity="0.6" strokeWidth="1">
            <line x1="200" y1="173" x2="60" y2="90" />
            <line x1="200" y1="173" x2="340" y2="240" />
            <circle cx="60" cy="90" r="3" fill="#2EA8FF" />
            <circle cx="340" cy="240" r="3" fill="#2EA8FF" />
          </g>
        )}

        {/* Stage 5: full context glow */}
        {stage >= 5 && <rect width="400" height="300" fill="#1688FF" opacity="0.06" />}
      </svg>
    </motion.div>
  );
}
