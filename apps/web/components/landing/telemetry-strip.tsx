"use client";

import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useRef } from "react";

interface Stat {
  value: number;
  label: string;
  suffix?: string;
}

// Explicitly illustrative — see the label under the strip. Never presented
// as a live count from any real deployment.
const STATS: Stat[] = [
  { value: 248, label: "Cameras Connected" },
  { value: 1842, label: "AI Events Today" },
  { value: 326, label: "Active Tracks" },
  { value: 7921, label: "Plate Reads" },
];

function Counter({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (v) => Math.round(v).toLocaleString());

  useEffect(() => {
    if (!inView) return;
    const controls = animate(motionValue, value, { duration: 1.4, ease: [0.16, 1, 0.3, 1] });
    return () => controls.stop();
  }, [inView, value, motionValue]);

  return <motion.span ref={ref}>{rounded}</motion.span>;
}

export function TelemetryStrip() {
  return (
    <section className="border-y border-lp-border bg-lp-bg-1/60 py-10">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-lp-success">
          <span className="h-1.5 w-1.5 rounded-full bg-lp-success lp-node-pulse" />
          Network Active
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {STATS.map((stat) => (
            <div key={stat.label}>
              <div className="font-mono text-3xl font-semibold text-lp-text-0 sm:text-4xl">
                <Counter value={stat.value} />
                {stat.suffix}
              </div>
              <div className="mt-1.5 text-xs text-lp-text-2">{stat.label}</div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-[11px] text-lp-text-2">Illustrative system telemetry.</p>
      </div>
    </section>
  );
}
