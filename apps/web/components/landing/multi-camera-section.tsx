"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { Reveal } from "./reveal";

const CAMERAS = [
  { id: "CAM-A", x: 60, y: 60 },
  { id: "CAM-B", x: 340, y: 90 },
  { id: "CAM-C", x: 200, y: 220 },
] as const;

const PATH = "M 60 60 C 150 40, 260 40, 340 90 C 320 160, 260 210, 200 220";

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
            MULTIPLE VIEWS.
            <br />
            <span className="text-lp-primary-2">ONE CONTINUOUS STORY.</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mx-auto mt-14 max-w-2xl overflow-hidden rounded border border-lp-border bg-lp-bg-0 p-6">
            <svg viewBox="0 0 400 260" className="h-auto w-full" aria-hidden="true">
              <path d={PATH} fill="none" stroke="rgb(30 58 95)" strokeWidth="2" strokeDasharray="4 6" />
              {/* CSS Motion Path (offset-path/offset-distance) — genuinely
                  the right tool for following a curved SVG path, supported
                  in all current major browsers (Safari since 16). On an
                  older browser that ignores it, the dot simply stays put
                  rather than erroring — a graceful, if less impressive,
                  degradation. */}
              {!prefersReducedMotion && (
                <motion.circle
                  r="4"
                  fill="rgb(87 188 255)"
                  animate={{ offsetDistance: ["0%", "100%"] }}
                  transition={{ duration: 6.6, repeat: Infinity, ease: "easeInOut" }}
                  style={{ offsetPath: `path('${PATH}')` }}
                />
              )}
              {CAMERAS.map((cam, i) => {
                const isActive = i === activeCamera;
                return (
                  <g key={cam.id}>
                    <circle
                      cx={cam.x}
                      cy={cam.y}
                      r={isActive ? 16 : 11}
                      fill="rgb(22 136 255)"
                      opacity={isActive ? 0.18 : 0.08}
                    />
                    <circle cx={cam.x} cy={cam.y} r={isActive ? 5 : 3.5} fill={isActive ? "rgb(87 188 255)" : "rgb(46 168 255)"} />
                    <text
                      x={cam.x}
                      y={cam.y - 22}
                      fill={isActive ? "#FFFFFF" : "rgb(148 163 184)"}
                      fontSize="11"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {cam.id}
                    </text>
                  </g>
                );
              })}
            </svg>

            <div className="mt-4 flex justify-center gap-2">
              {CAMERAS.map((cam, i) => (
                <span
                  key={cam.id}
                  className={`h-1.5 w-8 rounded-full transition-colors duration-300 ${
                    activeCamera === i ? "bg-lp-primary-2" : "bg-lp-border"
                  }`}
                />
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
