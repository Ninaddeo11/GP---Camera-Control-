"use client";

import { Reveal } from "./reveal";

const TIMELINE = [
  { time: "19:42:02", event: "Vehicle detected", source: "CAM-034" },
  { time: "19:42:04", event: "Track established", source: "#18492" },
  { time: "19:42:05", event: "Plate recognized", source: "MH12AB1234" },
  { time: "19:42:06", event: "Watchlist evaluated", source: "No match" },
  { time: "19:42:07", event: "Event correlated", source: "3 cameras" },
  { time: "19:42:08", event: "Alert generated", source: "Medium priority" },
];

export function FrameToIntelligenceSection() {
  return (
    <section className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <div className="relative aspect-[4/3] overflow-hidden rounded border border-lp-border bg-lp-bg-0">
            {/* Stylized night-road scene — vector, not a stock photo. */}
            <svg viewBox="0 0 400 300" className="h-full w-full" aria-hidden="true">
              <defs>
                <linearGradient id="ftosky" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0B1624" />
                  <stop offset="100%" stopColor="#050B12" />
                </linearGradient>
              </defs>
              <rect width="400" height="300" fill="url(#ftosky)" />
              <path d="M0 220 L160 120 L240 120 L400 220 Z" fill="#0B1624" opacity="0.7" />
              <path d="M160 300 L180 130 L220 130 L240 300 Z" fill="#07111C" />
              <path
                d="M180 130 L170 300 M220 130 L230 300"
                stroke="rgb(22 136 255)"
                strokeOpacity="0.3"
                strokeWidth="1"
              />
              {Array.from({ length: 6 }).map((_, i) => (
                <rect key={i} x={186 + i * 5} y={280 - i * 24} width="3" height="10" fill="rgb(46 168 255)" opacity={0.5 - i * 0.06} />
              ))}
            </svg>

            <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded bg-lp-bg-0/80 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-lp-success backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-lp-success lp-node-pulse" />
              CAM-034 · 19:42:05 · Live
            </div>

            <div className="absolute bottom-3 right-3 w-44 rounded border border-lp-primary/30 bg-lp-bg-0/90 p-3 text-[11px] backdrop-blur-sm">
              <div className="font-semibold uppercase tracking-wider text-lp-alert">Vehicle detected</div>
              <dl className="mt-2 space-y-1 text-lp-text-1">
                <div className="flex justify-between"><dt className="text-lp-text-2">Plate</dt><dd className="font-mono">MH12AB1234</dd></div>
                <div className="flex justify-between"><dt className="text-lp-text-2">Confidence</dt><dd>94.2%</dd></div>
                <div className="flex justify-between"><dt className="text-lp-text-2">Type</dt><dd>SUV</dd></div>
                <div className="flex justify-between"><dt className="text-lp-text-2">Color</dt><dd>White</dd></div>
                <div className="flex justify-between"><dt className="text-lp-text-2">Track</dt><dd>#18492</dd></div>
              </dl>
            </div>
          </div>
        </Reveal>

        <div>
          <Reveal>
            <h2 className="text-3xl font-bold leading-tight tracking-tight text-lp-text-0 sm:text-4xl">
              A FRAME SHOWS YOU
              <br />A MOMENT.
              <br />
              <span className="text-lp-primary-2">CONTEXT SHOWS YOU</span>
              <br />
              <span className="text-lp-primary-2">WHAT HAPPENED.</span>
            </h2>
          </Reveal>

          <ol className="mt-10 space-y-0">
            {TIMELINE.map((item, i) => (
              <Reveal key={item.time} delay={i * 0.1} direction="none">
                <li className="relative flex gap-4 pb-6 last:pb-0">
                  <div className="flex flex-col items-center">
                    <span className="h-2 w-2 shrink-0 rounded-full bg-lp-primary-2" />
                    {i < TIMELINE.length - 1 && <span className="mt-1 w-px flex-1 bg-lp-border" />}
                  </div>
                  <div className="flex flex-1 flex-wrap items-baseline justify-between gap-x-3 gap-y-1 pb-1">
                    <span className="font-mono text-xs text-lp-text-2">{item.time}</span>
                    <span className="flex-1 text-sm text-lp-text-0">{item.event}</span>
                    <span className="text-xs text-lp-text-2">{item.source}</span>
                  </div>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
