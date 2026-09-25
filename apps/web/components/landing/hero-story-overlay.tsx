"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import { getStoryNodePosition } from "./hero-network-background";

interface StoryCard {
  eyebrow: string;
  eyebrowTone: "alert" | "primary" | "success";
  content: React.ReactNode;
}

// Matches hero-network-background.tsx's STORY_NODES order — see hero.tsx
// for the shared timer driving both. Fictional demo values only.
//
// Typed as an explicit 4-tuple (not just `StoryCard[]`) so that
// `CARDS[0]` below is provably non-undefined under noUncheckedIndexedAccess
// — a plain array type doesn't carry a known length, so even a literal
// index into one is still `StoryCard | undefined` to the compiler.
const CARDS: readonly [StoryCard, StoryCard, StoryCard, StoryCard] = [
  {
    eyebrow: "Vehicle detected",
    eyebrowTone: "alert",
    content: null,
  },
  {
    eyebrow: "Track established",
    eyebrowTone: "primary",
    content: <div className="mt-1 font-mono text-xs text-lp-text-1">Track #18492</div>,
  },
  {
    eyebrow: "Plate recognized",
    eyebrowTone: "primary",
    content: (
      <>
        <div className="mt-1 font-mono text-sm text-lp-text-0">MH12AB1234</div>
        <div className="mt-0.5 text-[10px] text-lp-primary-2">94.2% confidence</div>
      </>
    ),
  },
  {
    eyebrow: "Event correlated",
    eyebrowTone: "success",
    content: <div className="mt-1 text-xs text-lp-text-1">3 cameras · 1 continuous story</div>,
  },
];

const TONE_CLASS = {
  alert: "text-lp-alert",
  primary: "text-lp-primary-2",
  success: "text-lp-success",
};

interface HeroStoryOverlayProps {
  storyPhase: number;
}

/**
 * Exactly one floating card at a time, positioned near whichever node
 * hero-network-background.tsx is currently highlighting for this phase —
 * brief section 8: "Do not have all panels visible simultaneously." Hidden
 * below lg (brief section 37: reduce density on mobile rather than
 * cramming floating overlays onto a small screen).
 */
export function HeroStoryOverlay({ storyPhase }: HeroStoryOverlayProps) {
  const prefersReducedMotion = useReducedMotion();
  const card = CARDS[storyPhase % CARDS.length] ?? CARDS[0];
  const pos = getStoryNodePosition(storyPhase);

  // Clamp so the card never renders flush against an edge.
  const left = Math.min(78, Math.max(4, pos.leftPct));
  const top = Math.min(70, Math.max(6, pos.topPct));

  return (
    <div className="pointer-events-none absolute inset-0 hidden lg:block" aria-hidden="true">
      <AnimatePresence mode="wait">
        <motion.div
          key={storyPhase}
          initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 10, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -6, scale: 0.98 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="absolute w-48 -translate-x-1/2 rounded border border-lp-border bg-lp-bg-1/85 p-3 shadow-[0_0_30px_-10px_rgba(22,136,255,0.4)] backdrop-blur-sm"
          style={{ left: `${left}%`, top: `${top}%` }}
        >
          <div className={`flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider ${TONE_CLASS[card.eyebrowTone]}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {card.eyebrow}
          </div>
          {card.content}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
