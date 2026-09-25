"use client";

import { Reveal } from "./reveal";

const FLOW = [
  "Cameras",
  "Stream Gateway",
  "AI Vision",
  "Tracking",
  "ANPR",
  "Event Engine",
  "Intelligence",
  "Command Center",
];

// Matches what's actually running (see README.md "Architecture") — not
// an aspirational diagram.
const DATA_LAYER = ["PostgreSQL / PostGIS", "Redis", "Object Storage", "Audit Layer", "Analytics"];

export function ArchitectureSection() {
  return (
    <section id="architecture" className="py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <Reveal className="text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">Architecture</h2>
        </Reveal>

        <Reveal delay={0.1}>
          <ol className="mx-auto mt-14 flex max-w-xs flex-col items-center">
            {FLOW.map((step, i) => (
              <li key={step} className="flex flex-col items-center">
                <span className="rounded border border-lp-primary/30 bg-lp-primary/10 px-6 py-2.5 text-sm font-medium text-lp-text-0">
                  {step}
                </span>
                {i < FLOW.length - 1 && <span className="my-1 h-6 w-px bg-lp-border" aria-hidden="true" />}
              </li>
            ))}
          </ol>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-14 flex flex-wrap justify-center gap-3 border-t border-lp-border pt-10">
            {DATA_LAYER.map((item) => (
              <span
                key={item}
                className="rounded border border-lp-border px-4 py-2 font-mono text-xs text-lp-text-2"
              >
                {item}
              </span>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
