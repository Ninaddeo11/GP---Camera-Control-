"use client";

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { type PointerEvent as ReactPointerEvent } from "react";

interface NetworkNode {
  id: string;
  x: number;
  y: number;
}

// Fixed node layout (percent coordinates of a 1000x600 viewBox) — a stylized
// aerial intersection grid, not a real map. Deliberately abstract vector
// graphics rather than a photographic city image (none is available, and a
// convincing photoreal city-at-night render is its own asset pipeline) —
// this is the "living digital representation of a city" the brief asks
// for, built as something actually achievable, fast, and tasteful.
const NODES: NetworkNode[] = [
  { id: "n1", x: 140, y: 120 },
  { id: "n2", x: 420, y: 90 },
  { id: "n3", x: 700, y: 140 },
  { id: "n4", x: 860, y: 260 },
  { id: "n5", x: 620, y: 320 },
  { id: "n6", x: 330, y: 300 },
  { id: "n7", x: 120, y: 420 },
  { id: "n8", x: 480, y: 460 },
  { id: "n9", x: 780, y: 460 },
];

const LINKS: [string, string][] = [
  ["n1", "n2"], ["n2", "n3"], ["n3", "n4"], ["n4", "n5"], ["n5", "n6"],
  ["n6", "n1"], ["n6", "n7"], ["n5", "n8"], ["n8", "n9"], ["n4", "n9"], ["n2", "n6"],
];

const byId: Record<string, NetworkNode> = Object.fromEntries(NODES.map((n): [string, NetworkNode] => [n.id, n]));

// NODES/LINKS/VEHICLE_PATHS are fixed, hand-authored constants — every id
// referenced by a link is guaranteed present in NODES by construction, but
// `byId`'s index signature is still `Record<string, NetworkNode>`
// (TypeScript can't prove a string literal always has a matching key), so
// `noUncheckedIndexedAccess` still types a bare `byId[id]` as possibly
// undefined. This throws loudly on a genuine authoring typo instead of
// silently rendering a broken line to `undefined` coordinates.
function getNode(id: string): NetworkNode {
  const node = byId[id];
  if (!node) throw new Error(`hero-network-background: unknown node id "${id}"`);
  return node;
}

const VEHICLE_PATHS: [string, string][] = [
  ["n1", "n2"], ["n3", "n4"], ["n6", "n7"], ["n5", "n8"],
];

// The "detection story" cycles through these four nodes — hero.tsx drives
// `storyPhase` on a timer and both this background and hero-story-overlay
// react to the same value, so the highlighted node, its correlation lines,
// and the floating caption cards all stay in sync without literally
// hard-coding a 9-step director sequence (see hero.tsx's comment on that
// scope decision).
export const STORY_NODES = ["n2", "n5", "n4", "n7"] as const;
const STORY_CORRELATIONS: Record<string, string[]> = {
  n2: ["n1", "n3", "n6"],
  n5: ["n4", "n6", "n8"],
  n4: ["n3", "n5", "n9"],
  n7: ["n1", "n6"],
};

/** Percent-space position (0-100) of the story node for phase `n` — used by
 * hero-story-overlay.tsx to place each caption card near its node without
 * duplicating the node layout data. Approximate (the SVG uses
 * `preserveAspectRatio="xMidYMid slice"`, which crops rather than letterboxes,
 * so this isn't pixel-perfect at every viewport width) — acceptable for a
 * decorative caption card, not a precisely-anchored control.
 */
export function getStoryNodePosition(phase: number): { leftPct: number; topPct: number } {
  const id = STORY_NODES[phase % STORY_NODES.length] ?? STORY_NODES[0];
  const node = getNode(id);
  return { leftPct: (node.x / 1000) * 100, topPct: (node.y / 600) * 100 };
}

interface HeroNetworkBackgroundProps {
  storyPhase: number;
}

export function HeroNetworkBackground({ storyPhase }: HeroNetworkBackgroundProps) {
  const prefersReducedMotion = useReducedMotion();
  const activeNodeId = STORY_NODES[storyPhase % STORY_NODES.length] ?? STORY_NODES[0];
  const activeNode = getNode(activeNodeId);
  const correlatedIds = STORY_CORRELATIONS[activeNodeId] ?? [];

  // Subtle pointer-reactive parallax (brief section 9/10) — two depth
  // groups (the grid/links vs. the nodes) drift a few px apart from the
  // cursor, springed for smoothness. Disabled under prefers-reduced-motion
  // entirely, not just slowed down.
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const springX = useSpring(pointerX, { stiffness: 60, damping: 20 });
  const springY = useSpring(pointerY, { stiffness: 60, damping: 20 });
  const farX = useTransform(springX, (v) => v * 6);
  const farY = useTransform(springY, (v) => v * 6);
  const nearX = useTransform(springX, (v) => v * 14);
  const nearY = useTransform(springY, (v) => v * 14);

  function handlePointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (prefersReducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    pointerX.set(((e.clientX - rect.left) / rect.width - 0.5) * 2);
    pointerY.set(((e.clientY - rect.top) / rect.height - 0.5) * 2);
  }

  return (
    <div
      className="pointer-events-auto absolute inset-0 overflow-hidden"
      onPointerMove={handlePointerMove}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 1000 600"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
      >
        <defs>
          <pattern id="lp-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0 L0 0 0 40" fill="none" stroke="rgb(30 58 95)" strokeWidth="0.5" opacity="0.35" />
          </pattern>
          <radialGradient id="lp-vignette" cx="50%" cy="38%" r="65%">
            <stop offset="0%" stopColor="rgb(11 22 36)" stopOpacity="0" />
            <stop offset="100%" stopColor="rgb(3 7 13)" stopOpacity="0.92" />
          </radialGradient>
        </defs>

        <rect width="1000" height="600" fill="url(#lp-grid)" />

        <motion.g style={prefersReducedMotion ? undefined : { x: farX, y: farY }}>
          {LINKS.map(([a, b], i) => {
            const from = getNode(a);
            const to = getNode(b);
            return (
              <line
                key={`${a}-${b}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="rgb(22 136 255)"
                strokeOpacity="0.22"
                strokeWidth="1"
                className={prefersReducedMotion ? undefined : "lp-data-flow"}
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            );
          })}

          {!prefersReducedMotion &&
            VEHICLE_PATHS.map(([a, b], i) => {
              const from = getNode(a);
              const to = getNode(b);
              return (
                <motion.circle
                  key={`vehicle-${a}-${b}`}
                  r="2.2"
                  fill="rgb(105 199 255)"
                  initial={{ cx: from.x, cy: from.y, opacity: 0 }}
                  animate={{
                    cx: [from.x, to.x, from.x],
                    cy: [from.y, to.y, from.y],
                    opacity: [0, 1, 1, 0],
                  }}
                  transition={{ duration: 6 + i, repeat: Infinity, ease: "easeInOut", delay: i * 1.3 }}
                />
              );
            })}
        </motion.g>

        <motion.g style={prefersReducedMotion ? undefined : { x: nearX, y: nearY }}>
          {/* Correlation glow: lines from the currently "active" story node
              to its related nodes brighten — the visual counterpart to
              hero-story-overlay's "Event correlated" caption. */}
          {correlatedIds.map((id) => {
            const other = getNode(id);
            return (
              <motion.line
                key={`corr-${activeNodeId}-${id}`}
                x1={activeNode.x}
                y1={activeNode.y}
                x2={other.x}
                y2={other.y}
                stroke="rgb(87 188 255)"
                strokeWidth="1.4"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 0.8, 0.4] }}
                transition={{ duration: 1.2, ease: "easeOut" }}
              />
            );
          })}

          {NODES.map((node, i) => {
            const isActive = node.id === activeNodeId;
            return (
              <g key={node.id}>
                <circle cx={node.x} cy={node.y} r={isActive ? 16 : 10} fill="rgb(22 136 255)" opacity={isActive ? 0.14 : 0.08} />
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={isActive ? 4.5 : 3}
                  fill={isActive ? "rgb(87 188 255)" : "rgb(46 168 255)"}
                  initial={{ opacity: 0.4 }}
                  animate={prefersReducedMotion ? { opacity: 0.7 } : { opacity: [0.4, 1, 0.4] }}
                  transition={
                    prefersReducedMotion ? undefined : { duration: 2.6, repeat: Infinity, delay: i * 0.25, ease: "easeInOut" }
                  }
                />
                {isActive && (
                  <motion.rect
                    x={node.x - 22}
                    y={node.y - 16}
                    width="44"
                    height="32"
                    rx="3"
                    fill="none"
                    stroke="rgb(255 77 90)"
                    strokeWidth="1.2"
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 0.85, scale: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.4 }}
                  />
                )}
              </g>
            );
          })}
        </motion.g>

        <rect width="1000" height="600" fill="url(#lp-vignette)" />
      </svg>
    </div>
  );
}
