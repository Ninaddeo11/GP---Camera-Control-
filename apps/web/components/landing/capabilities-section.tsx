"use client";

import { Reveal } from "./reveal";

// Editorial alternating rows rather than a repeated card grid (brief
// section 16 — "must not look like a dashboard... avoid a card-grid
// pattern here specifically since it has been used elsewhere on the
// page"). Each capability gets room for a short paragraph, not a
// three-word blurb.
const CAPABILITIES = [
  {
    title: "Live Video",
    copy: "A unified view across distributed cameras, without switching between disconnected tools.",
    icon: (
      <path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z M16 10l5-3v10l-5-3" />
    ),
  },
  {
    title: "AI Vision",
    copy: "Objects are detected and classified as they appear, turning raw video into structured signal.",
    icon: <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />,
  },
  {
    title: "Smart Tracking",
    copy: "Movement is followed across frames, cameras and locations as one continuous path, not isolated clips.",
    icon: <path d="M4 5h4v4H4V5Z M16 15h4v4h-4v-4Z M8 7h5a3 3 0 0 1 3 3v5" />,
  },
  {
    title: "ANPR",
    copy: "Vehicle imagery becomes a searchable, correlatable identity signal your team can act on.",
    icon: <path d="M3 8h18v8H3V8Z M6 12h4 M14 12h4" />,
  },
  {
    title: "Event Intelligence",
    copy: "Individual detections are correlated into meaningful events, connected across cameras and time.",
    icon: <path d="M12 2v6l4 2 M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />,
  },
  {
    title: "Evidence",
    copy: "What matters is preserved, verified and exportable, with a clear chain of custody.",
    icon: <path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z M9 13l2 2 4-4" />,
  },
];

export function CapabilitiesSection() {
  return (
    <section id="capabilities" className="py-24 sm:py-32">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            ONE PLATFORM.
            <br />
            <span className="text-lp-primary-2">EVERY SIGNAL.</span>
          </h2>
          <p className="mt-5 text-base text-lp-text-1">
            From live video to actionable intelligence, GP Sentinel connects every
            layer of the camera ecosystem.
          </p>
        </Reveal>

        <div className="mt-16 divide-y divide-lp-border">
          {CAPABILITIES.map((cap, i) => (
            <Reveal key={cap.title} delay={Math.min(i * 0.05, 0.2)}>
              <div
                className={`flex flex-col items-center gap-6 py-10 sm:gap-10 ${
                  i % 2 === 1 ? "sm:flex-row-reverse" : "sm:flex-row"
                }`}
              >
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border border-lp-primary/30 bg-lp-primary/10 text-lp-primary-2">
                  <svg
                    width="26"
                    height="26"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {cap.icon}
                  </svg>
                </div>
                <div className={`text-center sm:text-left ${i % 2 === 1 ? "sm:text-right" : ""}`}>
                  <h3 className="text-lg font-semibold uppercase tracking-wider text-lp-text-0">
                    {cap.title}
                  </h3>
                  <p className="mt-2 max-w-lg text-sm leading-relaxed text-lp-text-2">{cap.copy}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
