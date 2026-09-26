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

import { CameraFeedThumb } from "./camera-feed-thumb";

const STAGES = ["See", "Detect", "Track", "Recognize", "Connect", "Understand"] as const;

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
 * "FROM VISION TO ACTION" (redesign brief sections 23/24) — a sticky,
 * scroll-scrubbed sequence where ONE real camera view (a crop of the
 * licensed hero photo, see camera-feed-thumb.tsx) progressively gains
 * annotation layers as the user scrolls: a bounding box, a movement
 * trail, an identity card, connections to other cameras, a final
 * "INTELLIGENCE" label. This is deliberately real-photo-based rather
 * than six unrelated icon cards or six separate stock photos — the brief
 * is explicit that a real visual should carry the story and that "the
 * same vehicle should visually continue through the stages."
 *
 * Falls back to a simple stacked list under prefers-reduced-motion, since
 * pinning the viewport for several scroll-lengths is itself a strong
 * motion effect some users want to avoid.
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
      <section id="intelligence" className="py-24 sm:py-28">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-lp-secondary">
            From Vision to Action
          </p>
          <ol className="mt-8 space-y-6">
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
    <section id="intelligence" ref={containerRef} className="relative h-[600vh]">
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div className="relative aspect-[4/3] overflow-hidden rounded border border-lp-border bg-lp-bg-0">
            {STAGES.map((_, i) => (
              <StageVisual key={i} stage={i} scrollYProgress={scrollYProgress} total={STAGES.length} />
            ))}
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-lp-secondary">
              From Vision to Action
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
      <CameraFeedThumb focusX={38} focusY={58} zoom={280} className="absolute inset-0" />
      <div className="absolute inset-0 bg-gradient-to-t from-lp-bg-00/75 via-lp-bg-00/10 to-lp-bg-00/30" />

      <svg viewBox="0 0 400 300" className="absolute inset-0 h-full w-full" aria-hidden="true">
        {/* Stage 1+ (Detect): bounding box on the vehicle */}
        {stage >= 1 && (
          <rect x="182" y="150" width="40" height="42" rx="2" fill="none" stroke="#FF4D5A" strokeWidth="1.5" />
        )}

        {/* Stage 2+ (Track): movement trail */}
        {stage >= 2 && (
          <path
            d="M202 192 C 196 216, 190 238, 182 258"
            fill="none"
            stroke="#57BCFF"
            strokeWidth="1.5"
            strokeDasharray="3 5"
          />
        )}

        {/* Stage 3+ (Recognize): plate/identity card */}
        {stage >= 3 && (
          <g>
            <rect x="236" y="140" width="118" height="42" rx="3" fill="#07111C" fillOpacity="0.85" stroke="#1688FF" strokeOpacity="0.5" />
            <text x="246" y="157" fill="#94A3B8" fontSize="8" fontFamily="monospace">
              PLATE SIGNAL
            </text>
            <text x="246" y="172" fill="#FFFFFF" fontSize="10" fontFamily="monospace">
              MH12AB1234
            </text>
          </g>
        )}

        {/* Stage 4+ (Connect): links to other camera nodes */}
        {stage >= 4 && (
          <g stroke="#2EA8FF" strokeOpacity="0.6" strokeWidth="1">
            <line x1="202" y1="171" x2="55" y2="70" />
            <line x1="202" y1="171" x2="355" y2="230" />
            <circle cx="55" cy="70" r="4" fill="#0B1624" stroke="#2EA8FF" strokeWidth="1.5" />
            <circle cx="355" cy="230" r="4" fill="#0B1624" stroke="#2EA8FF" strokeWidth="1.5" />
          </g>
        )}
      </svg>

      {/* Stage 5 (Understand): full context label — pinned to the bottom
          edge, not centered, so it never overlaps the plate/identity card
          from stage 3 which is still shown cumulatively at this point. */}
      {stage >= 5 && (
        <div className="absolute inset-0 bg-lp-primary/10">
          <div className="absolute inset-x-0 bottom-4 flex justify-center">
            <span className="rounded-full border border-lp-primary/40 bg-lp-bg-0/85 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white backdrop-blur-sm">
              Intelligence
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}
