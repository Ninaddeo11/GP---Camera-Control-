"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { Reveal } from "./reveal";

const STEPS = ["Plate detected", "Text extracted", "Identity signal created"] as const;
const DEMO_PLATE = "KA05MJ7781"; // fictional demo value

export function AnprSection() {
  const prefersReducedMotion = useReducedMotion();
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion) return;
    const id = setInterval(() => setStep((s) => (s + 1) % (STEPS.length + 1)), 1600);
    return () => clearInterval(id);
  }, [prefersReducedMotion]);

  const effectiveStep = prefersReducedMotion ? STEPS.length : step;

  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <div className="relative aspect-[4/3] overflow-hidden rounded border border-lp-border bg-lp-bg-0">
            <svg viewBox="0 0 400 300" className="h-full w-full" aria-hidden="true">
              <defs>
                <linearGradient id="anpr-sky" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0B1624" />
                  <stop offset="100%" stopColor="#03070D" />
                </linearGradient>
              </defs>
              <rect width="400" height="300" fill="url(#anpr-sky)" />
              <rect x="130" y="150" width="140" height="80" rx="6" fill="#07111C" stroke="#1E3A5F" strokeWidth="1.5" />
              <rect x="160" y="195" width="80" height="22" rx="2" fill="#0B1624" stroke={effectiveStep >= 1 ? "#FF4D5A" : "#1E3A5F"} strokeWidth="1.5" />
              {effectiveStep >= 2 && (
                <text x="170" y="211" fill="#FFFFFF" fontSize="11" fontFamily="monospace">
                  {DEMO_PLATE}
                </text>
              )}
            </svg>

            <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
              <AnimatePresence mode="wait">
                {effectiveStep < STEPS.length && (
                  <motion.div
                    key={effectiveStep}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.3 }}
                    className="whitespace-nowrap rounded border border-lp-primary/30 bg-lp-bg-1/90 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-lp-primary-2 backdrop-blur-sm"
                  >
                    {STEPS[effectiveStep]}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </Reveal>

        <div>
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
              A PLATE.
              <br />
              <span className="text-lp-primary-2">A SEARCHABLE SIGNAL.</span>
            </h2>
            <p className="mt-6 max-w-md text-base leading-relaxed text-lp-text-1">
              GP Sentinel converts vehicle imagery into an identity signal — not a
              stored photograph, but a searchable, correlatable piece of context
              your team can act on.
            </p>
          </Reveal>

          <Reveal delay={0.15}>
            <div
              className={`mt-8 inline-flex items-center gap-3 rounded border border-lp-border bg-lp-bg-1/50 px-5 py-3 transition-opacity duration-500 ${
                effectiveStep >= STEPS.length ? "opacity-100" : "opacity-40"
              }`}
            >
              <span className="h-2 w-2 rounded-full bg-lp-success" />
              <span className="font-mono text-sm text-lp-text-0">{DEMO_PLATE}</span>
              <span className="text-xs text-lp-text-2">demo value</span>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
