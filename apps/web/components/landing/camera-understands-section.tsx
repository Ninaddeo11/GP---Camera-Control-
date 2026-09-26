"use client";

import { Reveal } from "./reveal";

const OUTCOMES = [
  {
    label: "Better Awareness",
    icon: <circle cx="12" cy="12" r="8" />,
  },
  {
    label: "Faster Response",
    icon: <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />,
  },
  {
    label: "Safer Communities",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="3.5" />
      </>
    ),
  },
];

export function CameraUnderstandsSection() {
  return (
    <section id="platform" className="py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-lp-secondary">
            From Vision to Action
          </p>
        </Reveal>

        <div className="mt-6 grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <Reveal>
            <h2 className="text-3xl font-bold leading-tight tracking-tight text-lp-text-0 sm:text-4xl lg:text-5xl">
              A CAMERA SEES.
              <br />
              <span className="text-lp-primary-2">SENTINEL UNDERSTANDS.</span>
            </h2>
          </Reveal>

          <div>
            <Reveal delay={0.1}>
              <p className="text-base leading-relaxed text-lp-text-1 sm:text-lg">
                Every frame can be more than a video.
              </p>
              <p className="mt-4 max-w-lg text-base leading-relaxed text-lp-text-1">
                GP Sentinel turns visual information into context, connecting
                what happened, where it happened and how events relate across
                your environment.
              </p>
            </Reveal>

            <Reveal delay={0.2}>
              <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
                {OUTCOMES.map((outcome) => (
                  <div key={outcome.label} className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-4">
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      className="shrink-0 text-lp-primary-2"
                      aria-hidden="true"
                    >
                      {outcome.icon}
                    </svg>
                    <span className="text-xs font-semibold uppercase tracking-wider text-lp-text-0">
                      {outcome.label}
                    </span>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}
