"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { Reveal } from "./reveal";

interface Stage {
  word: string;
  visual: React.ReactNode;
}

const STAGES: readonly [Stage, Stage, Stage, Stage, Stage, Stage] = [
  {
    word: "See",
    visual: (
      <rect x="20" y="20" width="160" height="100" rx="4" fill="none" stroke="#1688FF" strokeOpacity="0.6" strokeWidth="1.5" />
    ),
  },
  {
    word: "Detect",
    visual: (
      <>
        <rect x="20" y="20" width="160" height="100" rx="4" fill="none" stroke="#1E3A5F" strokeWidth="1.5" />
        <rect x="80" y="55" width="40" height="40" rx="2" fill="none" stroke="#FF4D5A" strokeWidth="1.5" />
      </>
    ),
  },
  {
    word: "Track",
    visual: (
      <>
        <rect x="20" y="20" width="160" height="100" rx="4" fill="none" stroke="#1E3A5F" strokeWidth="1.5" />
        <path d="M60 100 C 80 80, 100 60, 130 45" fill="none" stroke="#57BCFF" strokeWidth="1.5" strokeDasharray="3 4" />
        <circle cx="130" cy="45" r="3" fill="#57BCFF" />
      </>
    ),
  },
  {
    word: "Recognize",
    visual: (
      <>
        <rect x="20" y="20" width="160" height="100" rx="4" fill="none" stroke="#1E3A5F" strokeWidth="1.5" />
        <rect x="55" y="60" width="90" height="24" rx="2" fill="#07111C" stroke="#1688FF" strokeOpacity="0.6" />
        <text x="65" y="76" fill="#FFFFFF" fontSize="10" fontFamily="monospace">
          MH12AB1234
        </text>
      </>
    ),
  },
  {
    word: "Connect",
    visual: (
      <g stroke="#2EA8FF" strokeWidth="1.2" strokeOpacity="0.7">
        <line x1="40" y1="30" x2="100" y2="70" />
        <line x1="160" y1="30" x2="100" y2="70" />
        <line x1="40" y1="110" x2="100" y2="70" />
        <line x1="160" y1="110" x2="100" y2="70" />
        <circle cx="100" cy="70" r="4" fill="#57BCFF" />
        <circle cx="40" cy="30" r="2.5" fill="#2EA8FF" />
        <circle cx="160" cy="30" r="2.5" fill="#2EA8FF" />
        <circle cx="40" cy="110" r="2.5" fill="#2EA8FF" />
        <circle cx="160" cy="110" r="2.5" fill="#2EA8FF" />
      </g>
    ),
  },
  {
    word: "Understand",
    visual: (
      <>
        <rect x="20" y="20" width="160" height="100" rx="4" fill="#1688FF" fillOpacity="0.08" stroke="#1688FF" strokeWidth="1.5" />
        <text x="100" y="76" fill="#FFFFFF" fontSize="11" fontFamily="monospace" textAnchor="middle">
          INTELLIGENCE
        </text>
      </>
    ),
  },
];

/**
 * Hover-driven on desktop (matches the brief's "hovering over an element
 * activates its corresponding visualization"); auto-cycles when nothing is
 * hovered, and continuously auto-cycles on touch devices where hover
 * doesn't apply. Frozen on the first stage under prefers-reduced-motion.
 */
export function PipelineWordsSection() {
  const prefersReducedMotion = useReducedMotion();
  const [hovered, setHovered] = useState<number | null>(null);
  const [autoIndex, setAutoIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion || hovered !== null) return;
    const id = setInterval(() => setAutoIndex((i) => (i + 1) % STAGES.length), 2400);
    return () => clearInterval(id);
  }, [prefersReducedMotion, hovered]);

  const activeIndex = hovered ?? autoIndex;
  const active = STAGES[activeIndex] ?? STAGES[0];

  return (
    <section id="intelligence" className="py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            EVERY SIGNAL,
            <br />
            <span className="text-lp-primary-2">ONE JOURNEY.</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-16 grid grid-cols-1 gap-10 lg:grid-cols-[1fr_320px] lg:items-center">
            <div className="flex flex-wrap items-center justify-center gap-x-1 gap-y-3">
              {STAGES.map((stage, i) => (
                <div key={stage.word} className="flex items-center">
                  <button
                    type="button"
                    onMouseEnter={() => setHovered(i)}
                    onMouseLeave={() => setHovered(null)}
                    onFocus={() => setHovered(i)}
                    onBlur={() => setHovered(null)}
                    className={`rounded px-3 py-2 text-base font-semibold uppercase tracking-wide transition-colors sm:text-xl ${
                      activeIndex === i ? "text-lp-primary-2" : "text-lp-text-2 hover:text-lp-text-0"
                    }`}
                  >
                    {stage.word}
                  </button>
                  {i < STAGES.length - 1 && <span className="text-lp-text-2">→</span>}
                </div>
              ))}
            </div>

            <div className="aspect-[10/7] overflow-hidden rounded border border-lp-border bg-lp-bg-1/40">
              <AnimatePresence mode="wait">
                <motion.svg
                  key={active.word}
                  viewBox="0 0 200 140"
                  className="h-full w-full"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  aria-hidden="true"
                >
                  {active.visual}
                </motion.svg>
              </AnimatePresence>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
