"use client";

import { motion } from "framer-motion";

import { Reveal } from "./reveal";

const CAPABILITIES = [
  {
    title: "Live Video",
    desc: "Monitor distributed cameras from a unified command interface.",
    icon: (
      <path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z M16 10l5-3v10l-5-3" />
    ),
  },
  {
    title: "AI Vision",
    desc: "Detect and classify objects in real time.",
    icon: <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />,
  },
  {
    title: "Smart Tracking",
    desc: "Follow objects across frames, cameras and locations.",
    icon: <path d="M4 5h4v4H4V5Z M16 15h4v4h-4v-4Z M8 7h5a3 3 0 0 1 3 3v5" />,
  },
  {
    title: "ANPR",
    desc: "Convert vehicle imagery into searchable plate intelligence.",
    icon: <path d="M3 8h18v8H3V8Z M6 12h4 M14 12h4" />,
  },
  {
    title: "Event Intelligence",
    desc: "Transform detections into meaningful operational events.",
    icon: <path d="M12 2v6l4 2 M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z" />,
  },
  {
    title: "Evidence",
    desc: "Preserve, verify and export auditable evidence.",
    icon: <path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z M9 13l2 2 4-4" />,
  },
];

export function CapabilitiesSection() {
  return (
    <section id="intelligence" className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
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

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap, i) => (
            <Reveal key={cap.title} delay={i * 0.06}>
              <motion.div
                whileHover={{ y: -4, borderColor: "rgb(22 136 255 / 0.5)" }}
                className="group h-full rounded border border-lp-border bg-lp-bg-1/50 p-6 transition-shadow hover:shadow-[0_0_40px_-16px_rgba(22,136,255,0.5)]"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded border border-lp-primary/30 bg-lp-primary/10 text-lp-primary-2 transition-transform group-hover:scale-110">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    {cap.icon}
                  </svg>
                </div>
                <h3 className="mt-4 text-sm font-semibold uppercase tracking-wider text-lp-text-0">
                  {cap.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-lp-text-2">{cap.desc}</p>
                <span className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-lp-primary-2 opacity-0 transition-opacity group-hover:opacity-100">
                  Learn more <span className="transition-transform group-hover:translate-x-1">→</span>
                </span>
              </motion.div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
