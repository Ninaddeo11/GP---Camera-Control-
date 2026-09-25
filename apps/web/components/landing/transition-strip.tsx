"use client";

import { motion } from "framer-motion";

/**
 * Replaces the old telemetry strip (camera/event/track/plate counters) —
 * removed entirely per the brief: the public site must not expose any
 * operational statistics, real or illustrative. This is a pure visual
 * transition beat between the hero and the rest of the story.
 */
export function TransitionStrip() {
  return (
    <div className="border-y border-lp-border bg-lp-bg-1/40 py-14">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6 }}
          className="text-sm font-semibold uppercase tracking-[0.35em] text-lp-text-2"
        >
          From Vision <span className="text-lp-primary-2">to</span> Understanding
        </motion.p>
        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 1, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mt-6 h-px w-full max-w-md origin-center bg-gradient-to-r from-transparent via-lp-primary-2 to-transparent"
        />
      </div>
    </div>
  );
}
