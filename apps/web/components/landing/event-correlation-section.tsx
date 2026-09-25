"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { Reveal } from "./reveal";

const SIGNALS = ["Camera", "Vehicle", "Location", "Time", "Plate", "Movement", "Event"] as const;

const CENTER = { x: 200, y: 190 };
const RADIUS = 130;

function pointOnCircle(index: number, total: number): { x: number; y: number } {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2;
  return { x: CENTER.x + RADIUS * Math.cos(angle), y: CENTER.y + RADIUS * Math.sin(angle) };
}

/**
 * A radial signal graph that draws itself in once scrolled into view, then
 * converges on a center "INTELLIGENCE" label — a one-shot reveal (not a
 * continuous loop), triggered by IntersectionObserver via a ref rather
 * than Reveal's whileInView (this needs to know *when* it entered view to
 * kick off the staggered line-draw sequence, not just apply a variant).
 */
export function EventCorrelationSection() {
  const prefersReducedMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const [triggered, setTriggered] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setTriggered(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const active = triggered || Boolean(prefersReducedMotion);

  return (
    <section className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            INDIVIDUAL SIGNALS.
            <br />
            <span className="text-lp-primary-2">CONNECTED CONTEXT.</span>
          </h2>
        </Reveal>

        <div ref={containerRef} className="mx-auto mt-14 max-w-xl">
          <svg viewBox="0 0 400 380" className="h-auto w-full" aria-hidden="true">
            {SIGNALS.map((signal, i) => {
              const p = pointOnCircle(i, SIGNALS.length);
              return (
                <motion.line
                  key={`line-${signal}`}
                  x1={p.x}
                  y1={p.y}
                  x2={CENTER.x}
                  y2={CENTER.y}
                  stroke="rgb(46 168 255)"
                  strokeWidth="1"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={active ? { pathLength: 1, opacity: 0.5 } : {}}
                  transition={{ duration: 0.6, delay: prefersReducedMotion ? 0 : i * 0.12, ease: "easeOut" }}
                />
              );
            })}

            {SIGNALS.map((signal, i) => {
              const p = pointOnCircle(i, SIGNALS.length);
              return (
                <motion.g
                  key={signal}
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={active ? { opacity: 1, scale: 1 } : {}}
                  transition={{ duration: 0.4, delay: prefersReducedMotion ? 0 : i * 0.12 }}
                >
                  <circle cx={p.x} cy={p.y} r="20" fill="rgb(7 17 28)" stroke="rgb(30 58 95)" strokeWidth="1" />
                  <text x={p.x} y={p.y + 4} fill="#CBD5E1" fontSize="10" fontFamily="monospace" textAnchor="middle">
                    {signal}
                  </text>
                </motion.g>
              );
            })}

            <motion.g
              initial={{ opacity: 0, scale: 0.7 }}
              animate={active ? { opacity: 1, scale: 1 } : {}}
              transition={{ duration: 0.5, delay: prefersReducedMotion ? 0 : SIGNALS.length * 0.12 + 0.2 }}
            >
              <circle cx={CENTER.x} cy={CENTER.y} r="42" fill="rgb(22 136 255)" fillOpacity="0.12" stroke="rgb(46 168 255)" strokeWidth="1.5" />
              <text x={CENTER.x} y={CENTER.y + 5} fill="#FFFFFF" fontSize="12" fontFamily="monospace" textAnchor="middle">
                INTELLIGENCE
              </text>
            </motion.g>
          </svg>
        </div>
      </div>
    </section>
  );
}
