"use client";

import { Reveal } from "./reveal";

const STAGES = [
  { n: "01", title: "Capture", desc: "Live camera streams enter the platform." },
  { n: "02", title: "Detect", desc: "AI identifies vehicles, people and objects." },
  { n: "03", title: "Track", desc: "Objects are tracked across frames and cameras." },
  { n: "04", title: "Recognize", desc: "ANPR converts vehicle imagery into searchable identity signals." },
  { n: "05", title: "Correlate", desc: "Events are connected across time, cameras and jurisdictions." },
  { n: "06", title: "Respond", desc: "Operators receive alerts, intelligence and evidence." },
];

export function PipelineSection() {
  return (
    <section id="platform" className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            CAMERAS ARE ONLY
            <br />
            <span className="text-lp-primary-2">THE BEGINNING.</span>
          </h2>
          <p className="mt-5 text-base text-lp-text-1">
            A camera captures a frame. GP Sentinel turns that frame into context.
          </p>
        </Reveal>

        <div className="relative mt-20">
          {/* Connecting line — desktop only; each stage's own reveal timing
              gives the sense of the pipeline activating in sequence. */}
          <div
            className="absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-transparent via-lp-primary/40 to-transparent lg:block"
            aria-hidden="true"
          />
          <ol className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-6 lg:gap-6">
            {STAGES.map((stage, i) => (
              <Reveal key={stage.n} delay={i * 0.08}>
                <li className="relative">
                  <div className="relative z-10 mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-lp-primary/40 bg-lp-bg-0 font-mono text-sm text-lp-primary-2">
                    {stage.n}
                  </div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-lp-text-0">
                    {stage.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-lp-text-2">{stage.desc}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
