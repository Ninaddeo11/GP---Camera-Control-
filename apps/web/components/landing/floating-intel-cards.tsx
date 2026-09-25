"use client";

import { motion } from "framer-motion";

interface FloatingCard {
  position: string;
  delay: number;
  content: React.ReactNode;
}

// All data on this page is illustrative — see the "Illustrative" labels on
// the telemetry strip and the note under the search demo. Nothing here is
// a real camera, plate, or event.
const CARDS: FloatingCard[] = [
  {
    position: "left-[4%] top-[18%] hidden lg:block",
    delay: 0.2,
    content: (
      <>
        <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-lp-success">
          <span className="h-1.5 w-1.5 rounded-full bg-lp-success" /> CAM-021 · Live
        </div>
        <div className="mt-1.5 text-xs text-lp-text-1">Vehicle detected</div>
      </>
    ),
  },
  {
    position: "right-[3%] top-[12%] hidden lg:block",
    delay: 0.5,
    content: (
      <>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-lp-text-2">
          Plate detected
        </div>
        <div className="mt-1 font-mono text-sm text-lp-text-0">MH12AB1234</div>
        <div className="mt-0.5 text-[10px] text-lp-primary-2">94.2% confidence</div>
      </>
    ),
  },
  {
    position: "right-[8%] top-[46%] hidden lg:block",
    delay: 0.8,
    content: (
      <>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-lp-alert">
          Watchlist match
        </div>
        <div className="mt-1 text-xs text-lp-text-1">CAM-034 · 19:42:05</div>
      </>
    ),
  },
  {
    position: "left-[8%] top-[52%] hidden lg:block",
    delay: 1.1,
    content: (
      <>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-lp-text-2">
          Tracking
        </div>
        <div className="mt-1 font-mono text-xs text-lp-text-0">Vehicle #18492</div>
        <div className="mt-0.5 text-[10px] text-lp-text-2">Direction: North-East</div>
      </>
    ),
  },
];

export function FloatingIntelCards() {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      {CARDS.map((card, i) => (
        <motion.div
          key={i}
          className={`absolute w-48 rounded border border-lp-border bg-lp-bg-1/80 p-3 shadow-[0_0_30px_-10px_rgba(22,136,255,0.35)] backdrop-blur-sm ${card.position}`}
          initial={{ opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: card.delay, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.div
            animate={{ y: [0, -5, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: card.delay }}
          >
            {card.content}
          </motion.div>
        </motion.div>
      ))}
    </div>
  );
}
