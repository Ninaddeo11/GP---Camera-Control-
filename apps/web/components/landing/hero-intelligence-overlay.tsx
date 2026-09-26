"use client";

// Floating intelligence overlays for the hero — a small, fixed set (brief
// section 10: "2-3 camera panels... do NOT create 10 panels", section 15:
// "only use a handful") driven by one shared story-phase timeline (hero.tsx)
// so camera activation, the detection box, the tracking card, the plate
// panel, and the watchlist alert all appear as one coherent sequence
// instead of independent, unrelated widgets.
//
// Deliberately hidden below `sm` (brief section 34: mobile gets city ->
// hero text -> vehicle -> detection -> intelligence, not a shrunk desktop
// hero with five overlapping cards crammed onto a phone screen).

import { AnimatePresence, motion } from "framer-motion";

import { CameraFeedThumb } from "./camera-feed-thumb";

export const STORY_PHASE_COUNT = 7;
export const STORY_PHASE_DURATION_MS = 1500;

const DEMO_PLATE = "MH12AB1234"; // fictional demo value, matches the rest of the site

export function HeroIntelligenceOverlay({ phase }: { phase: number }) {
  const camerasActive = phase >= 1;
  const detectionVisible = phase >= 2 && phase < 6;
  const trackingVisible = phase >= 3 && phase < 6;
  const plateVisible = phase >= 4 && phase < 6;
  const alertVisible = phase === 5;

  return (
    <div className="pointer-events-none absolute inset-0 z-10 hidden sm:block">
      {/* Two camera feed panels (section 10) — not ten. Each is a distinct
          crop of the single real hero photo (camera-feed-thumb.tsx). */}
      <AnimatePresence>
        {camerasActive && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="absolute left-[54%] top-[14%] w-40 overflow-hidden rounded border border-lp-primary/30 bg-lp-bg-0/70 backdrop-blur-sm lg:w-48"
          >
            <div className="flex items-center justify-between px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-lp-text-1">
              <span className="flex items-center gap-1">
                <CameraGlyph /> CAM-021
              </span>
              <span className="flex items-center gap-1 text-lp-success">
                <span className="h-1.5 w-1.5 rounded-full bg-lp-success lp-node-pulse" /> Live
              </span>
            </div>
            <CameraFeedThumb focusX={18} focusY={60} zoom={340} className="h-16 w-full lg:h-20" />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {camerasActive && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="absolute left-[76%] top-[40%] w-36 overflow-hidden rounded border border-lp-primary/30 bg-lp-bg-0/70 backdrop-blur-sm lg:w-44"
          >
            <div className="flex items-center justify-between px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-lp-text-1">
              <span className="flex items-center gap-1">
                <CameraGlyph /> CAM-048
              </span>
              <span className="flex items-center gap-1 text-lp-success">
                <span className="h-1.5 w-1.5 rounded-full bg-lp-success lp-node-pulse" /> Live
              </span>
            </div>
            <CameraFeedThumb focusX={82} focusY={30} zoom={320} className="h-14 w-full lg:h-16" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* The detection box — a plain bounding box, not a card, appearing
          directly on the tracked vehicle's path (brief section 11). */}
      <AnimatePresence>
        {detectionVisible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute left-[54%] top-[46%] h-10 w-16 rounded-sm border-2 border-lp-alert/80 lg:h-12 lg:w-20"
          />
        )}
      </AnimatePresence>

      {/* Vehicle tracking card (section 12) — small, exactly two facts. */}
      <AnimatePresence>
        {trackingVisible && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute left-[58%] top-[56%] w-40 rounded border border-lp-primary/30 bg-lp-bg-0/80 p-2.5 text-[10px] backdrop-blur-sm lg:w-44"
          >
            <div className="font-semibold uppercase tracking-wider text-lp-primary-2">Vehicle Tracking</div>
            <div className="mt-1.5 flex items-center justify-between text-lp-text-1">
              <span className="text-lp-text-2">Track ID</span>
              <span className="font-mono text-lp-text-0">#18492</span>
            </div>
            <div className="mt-0.5 text-lp-text-2">3 cameras</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Plate recognition panel (section 13) — the largest overlay,
          lower-right, with a small real-photo crop standing in for a
          rear-vehicle still. */}
      <AnimatePresence>
        {plateVisible && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute bottom-[12%] right-[6%] flex w-64 items-center gap-3 rounded border border-lp-primary/30 bg-lp-bg-0/85 p-3 backdrop-blur-sm lg:w-72"
          >
            <CameraFeedThumb focusX={40} focusY={70} zoom={420} className="h-14 w-20 shrink-0 rounded-sm lg:h-16 lg:w-24" />
            <div className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-lp-primary-2">
                Plate Recognized
              </div>
              <div className="mt-1 truncate font-mono text-base font-semibold text-lp-text-0 lg:text-lg">
                {DEMO_PLATE}
              </div>
              <div className="mt-0.5 text-[11px] text-lp-text-2">94.2% confidence</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Watchlist alert (section 14) — red, ONLY here, briefly. */}
      <AnimatePresence>
        {alertVisible && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="absolute right-[8%] top-[16%] w-56 rounded border border-lp-alert/50 bg-lp-bg-0/90 p-3 backdrop-blur-sm"
          >
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-lp-alert">
              <span aria-hidden="true">&#9888;</span> Watchlist Match
            </div>
            <div className="mt-1.5 font-mono text-sm font-semibold text-lp-text-0">{DEMO_PLATE}</div>
            <div className="mt-0.5 text-[11px] text-lp-text-2">CAM-034 &middot; 19:42:05</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CameraGlyph() {
  return (
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z M16 10l5-3v10l-5-3" />
    </svg>
  );
}
