"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { CameraFeedThumb } from "./camera-feed-thumb";
import { Reveal } from "./reveal";

// Positions in a 400x260 coordinate space (percent-converted below for the
// HTML camera panels, used directly for the SVG path/dot).
const CAMERAS = [
  { id: "CAM-A", x: 60, y: 60, focusX: 15, focusY: 70 },
  { id: "CAM-B", x: 340, y: 90, focusX: 60, focusY: 25 },
  { id: "CAM-C", x: 200, y: 220, focusX: 85, focusY: 55 },
] as const;

const PATH = "M 60 60 C 150 40, 260 40, 340 90 C 320 160, 260 210, 200 220";
const VIEW_W = 400;
const VIEW_H = 260;

export function MultiCameraSection() {
  const prefersReducedMotion = useReducedMotion();
  const [activeCamera, setActiveCamera] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion) return;
    const id = setInterval(() => setActiveCamera((c) => (c + 1) % CAMERAS.length), 2200);
    return () => clearInterval(id);
  }, [prefersReducedMotion]);

  return (
    <section className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            ONE MOVEMENT.
            <br />
            <span className="text-lp-primary-2">MULTIPLE VIEWS.</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="relative mx-auto mt-14 aspect-[400/260] max-w-2xl overflow-visible rounded border border-lp-border bg-lp-bg-0">
            <svg
              viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
              className="absolute inset-0 h-full w-full"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path d={PATH} fill="none" stroke="rgb(30 58 95)" strokeWidth="2" strokeDasharray="4 6" />
              {/* CSS Motion Path is genuinely the right tool for following a
                  curved SVG path; degrades gracefully (dot stays put) on a
                  browser too old to support offset-path. */}
              {!prefersReducedMotion && (
                <motion.circle
                  r="4"
                  fill="rgb(87 188 255)"
                  animate={{ offsetDistance: ["0%", "100%"] }}
                  transition={{ duration: 6.6, repeat: Infinity, ease: "easeInOut" }}
                  style={{ offsetPath: `path('${PATH}')` }}
                />
              )}
            </svg>

            {CAMERAS.map((cam, i) => {
              const isActive = i === activeCamera;
              const leftPct = (cam.x / VIEW_W) * 100;
              const topPct = (cam.y / VIEW_H) * 100;
              return (
                <div
                  key={cam.id}
                  className="absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${leftPct}%`, top: `${topPct}%` }}
                >
                  <div
                    className={`w-24 overflow-hidden rounded border bg-lp-bg-0/90 backdrop-blur-sm transition-all duration-300 sm:w-28 ${
                      isActive ? "border-lp-primary-2 shadow-[0_0_24px_-6px_rgba(46,168,255,0.6)]" : "border-lp-border"
                    }`}
                  >
                    <div className="flex items-center justify-between px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wider text-lp-text-1">
                      <span>{cam.id}</span>
                      {isActive && <span className="h-1 w-1 rounded-full bg-lp-success lp-node-pulse" />}
                    </div>
                    <CameraFeedThumb
                      focusX={cam.focusX}
                      focusY={cam.focusY}
                      zoom={320}
                      className="h-12 w-full sm:h-14"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
