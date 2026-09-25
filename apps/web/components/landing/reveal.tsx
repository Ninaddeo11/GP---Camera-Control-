"use client";

import { motion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  /** "up" (default) for the common fade-up-on-scroll; "none" just fades. */
  direction?: "up" | "none";
}

const variants: Record<"up" | "none", Variants> = {
  up: {
    hidden: { opacity: 0, y: 24 },
    show: { opacity: 1, y: 0 },
  },
  none: {
    hidden: { opacity: 0 },
    show: { opacity: 1 },
  },
};

/**
 * The one scroll-triggered reveal primitive every landing section builds
 * on (brief section 23/24: motion should tell a story as the page scrolls,
 * but must never be so pervasive it hurts readability). Respects
 * prefers-reduced-motion globally via app/globals.css's .landing-page
 * media query, which collapses all animation durations to ~0 — Framer
 * Motion still runs the same code path, it just resolves instantly.
 */
export function Reveal({ children, className, delay = 0, direction = "up" }: RevealProps) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-80px" }}
      variants={variants[direction]}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
