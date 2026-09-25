"use client";

import { Reveal } from "./reveal";

const CHAIN = [
  "Camera",
  "Detection",
  "Track",
  "Plate",
  "Location",
  "Time",
  "Related Events",
  "Operational Intelligence",
];

export function EventIntelligenceSection() {
  return (
    <section className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            DETECTION IS NOT
            <br />
            INTELLIGENCE.
            <br />
            <span className="text-lp-primary-2">CONTEXT IS.</span>
          </h2>
        </Reveal>

        <div className="mt-16 flex flex-wrap items-center justify-center gap-x-2 gap-y-4">
          {CHAIN.map((item, i) => (
            <Reveal key={item} delay={i * 0.07} direction="none" className="flex items-center gap-2">
              <span
                className={`rounded-full border px-4 py-2 text-xs font-medium ${
                  i === CHAIN.length - 1
                    ? "border-lp-primary bg-lp-primary/15 text-lp-primary-2"
                    : "border-lp-border text-lp-text-1"
                }`}
              >
                {item}
              </span>
              {i < CHAIN.length - 1 && (
                <span className="text-lp-text-2" aria-hidden="true">
                  →
                </span>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
