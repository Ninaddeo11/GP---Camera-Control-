"use client";

import { AnimatePresence, motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef, useState } from "react";

import { Reveal } from "./reveal";

interface DemoNode {
  id: string;
  label: string;
  x: number;
  y: number;
  district: string;
  status: "live" | "event";
}

// All illustrative demo nodes — see the note beneath the map. No real
// camera_id, location, or status from the actual platform is ever shown
// on the public site.
const DEMO_NODES: DemoNode[] = [
  { id: "CAM-021", label: "CAM-021", x: 140, y: 120, district: "District A", status: "live" },
  { id: "CAM-034", label: "CAM-034", x: 420, y: 90, district: "District A", status: "event" },
  { id: "CAM-048", label: "CAM-048", x: 700, y: 150, district: "District B", status: "live" },
  { id: "CAM-052", label: "CAM-052", x: 860, y: 270, district: "District B", status: "live" },
  { id: "CAM-067", label: "CAM-067", x: 610, y: 330, district: "District B", status: "live" },
  { id: "CAM-073", label: "CAM-073", x: 320, y: 310, district: "District A", status: "live" },
  { id: "EVENT-18492", label: "Event 18492", x: 470, y: 220, district: "District A", status: "event" },
];

export function LivingNetworkSection() {
  const [selected, setSelected] = useState<DemoNode | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const frameRef = useRef<HTMLDivElement>(null);

  // "As the user scrolls, the camera should slowly travel through the
  // city" (brief section 20) — a subtle scroll-linked push-in on the whole
  // scene, not a literal free-roaming camera (which would need a much
  // larger canvas than the visible frame to travel across). Skipped
  // entirely under prefers-reduced-motion rather than just slowed down.
  const { scrollYProgress } = useScroll({ target: frameRef, offset: ["start end", "end start"] });
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [1, 1.05, 1]);

  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            SEE THE CITY
            <br />
            <span className="text-lp-primary-2">AS A LIVING NETWORK.</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div
            ref={frameRef}
            className="relative mt-14 aspect-[5/3] overflow-hidden rounded border border-lp-border bg-lp-bg-1/40"
          >
            <motion.div
              className="absolute inset-0"
              style={prefersReducedMotion ? undefined : { scale }}
            >
            <svg viewBox="0 0 1000 600" className="h-full w-full" aria-hidden="true">
              <defs>
                <pattern id="lp-net-grid" width="50" height="50" patternUnits="userSpaceOnUse">
                  <path d="M50 0 L0 0 0 50" fill="none" stroke="rgb(30 58 95)" strokeWidth="0.5" opacity="0.4" />
                </pattern>
              </defs>
              <rect width="1000" height="600" fill="url(#lp-net-grid)" />
              <path d="M0 300 H1000 M500 0 V600" stroke="rgb(30 58 95)" strokeWidth="1" opacity="0.6" />
              <text x="20" y="30" fill="rgb(148 163 184)" fontSize="14" fontFamily="monospace" opacity="0.6">
                DISTRICT A
              </text>
              <text x="820" y="30" fill="rgb(148 163 184)" fontSize="14" fontFamily="monospace" opacity="0.6">
                DISTRICT B
              </text>
            </svg>

            {DEMO_NODES.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => setSelected(node)}
                className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
                style={{ left: `${(node.x / 1000) * 100}%`, top: `${(node.y / 600) * 100}%` }}
                aria-label={`View demo details for ${node.label}`}
              >
                <span
                  className={`block h-3 w-3 rounded-full lp-node-pulse ${
                    node.status === "event" ? "bg-lp-alert" : "bg-lp-primary-2"
                  }`}
                />
                <span className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 whitespace-nowrap font-mono text-[10px] text-lp-text-2">
                  {node.label}
                </span>
              </button>
            ))}
            </motion.div>

            <AnimatePresence>
              {selected && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 6 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="absolute bottom-4 left-4 w-56 rounded border border-lp-primary/30 bg-lp-bg-0/95 p-4 text-xs backdrop-blur-sm"
                  role="dialog"
                  aria-label={`${selected.label} demo details`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-mono text-sm font-semibold text-lp-text-0">{selected.label}</div>
                      <div className="mt-0.5 text-lp-text-2">{selected.district}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelected(null)}
                      aria-label="Close"
                      className="text-lp-text-2 hover:text-lp-text-0"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-lp-text-1">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${selected.status === "event" ? "bg-lp-alert" : "bg-lp-success"}`}
                    />
                    {selected.status === "event" ? "Recent event" : "Live"}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <p className="mt-4 text-[11px] text-lp-text-2">
            Illustrative demo network. No real camera locations, statuses or event data are shown here.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
