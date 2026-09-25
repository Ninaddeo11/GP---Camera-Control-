"use client";

import { Reveal } from "./reveal";

// "From Pixels to Context" (brief section 14) — deliberately abstract and
// editorial rather than a mock event log: earlier drafts of this section
// rendered a fake timestamped detection feed (plate numbers, confidence
// scores, "Live" badges), which reads exactly like the real operational
// telemetry the brief says the public site must never expose. This version
// names the transformation instead of simulating it.
const STAGES = [
  { label: "VIDEO", desc: "A camera sees a moment." },
  { label: "OBJECT", desc: "A shape becomes a thing." },
  { label: "TRACK", desc: "A thing becomes a path." },
  { label: "IDENTITY", desc: "A path becomes a signal." },
  { label: "EVENT", desc: "A signal becomes meaning." },
  { label: "CONTEXT", desc: "Meaning becomes a decision." },
] as const;

export function FrameToIntelligenceSection() {
  return (
    <section className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            FROM PIXELS
            <br />
            <span className="text-lp-primary-2">TO CONTEXT.</span>
          </h2>
          <p className="mt-5 text-base leading-relaxed text-lp-text-1">
            A frame shows you a moment. Context shows you what happened.
          </p>
        </Reveal>

        <div className="mt-16 grid grid-cols-2 gap-x-4 gap-y-12 sm:grid-cols-3 lg:grid-cols-6">
          {STAGES.map((stage, i) => (
            <Reveal key={stage.label} delay={i * 0.08}>
              <div className="relative flex flex-col items-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-lp-primary/30 bg-lp-primary/10 font-mono text-xs text-lp-primary-2">
                  0{i + 1}
                </div>
                <h3 className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-lp-text-0">
                  {stage.label}
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-lp-text-2">{stage.desc}</p>
                {i < STAGES.length - 1 && (
                  <span
                    className="pointer-events-none absolute right-[-18px] top-6 hidden text-lp-border lg:block"
                    aria-hidden="true"
                  >
                    &rarr;
                  </span>
                )}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
