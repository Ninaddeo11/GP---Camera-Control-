"use client";

import { motion } from "framer-motion";

interface NetworkNode {
  id: string;
  x: number;
  y: number;
}

// Fixed node layout (percent coordinates of a 1000x600 viewBox) — a stylized
// aerial intersection grid, not a real map. Deliberately abstract vector
// graphics rather than a photographic city image (none is available, and a
// convincing photoreal city-at-night render is its own asset pipeline) —
// this is the "operational intelligence visualization" the brief asks for,
// built as something actually achievable and fast.
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
  ["n1", "n2"],
  ["n2", "n3"],
  ["n3", "n4"],
  ["n4", "n5"],
  ["n5", "n6"],
  ["n6", "n1"],
  ["n6", "n7"],
  ["n5", "n8"],
  ["n8", "n9"],
  ["n4", "n9"],
  ["n2", "n6"],
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

// A handful of "vehicles" drifting along a couple of the road links, purely
// decorative — brief section 7: "vehicles should have subtle movement."
const VEHICLE_PATHS: [string, string][] = [
  ["n1", "n2"],
  ["n3", "n4"],
  ["n6", "n7"],
  ["n5", "n8"],
];

export function HeroNetworkBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <svg
        viewBox="0 0 1000 600"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
        aria-hidden="true"
      >
        <defs>
          <pattern id="lp-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0 L0 0 0 40" fill="none" stroke="rgb(30 58 95)" strokeWidth="0.5" opacity="0.35" />
          </pattern>
          <radialGradient id="lp-vignette" cx="50%" cy="38%" r="65%">
            <stop offset="0%" stopColor="rgb(11 22 36)" stopOpacity="0" />
            <stop offset="100%" stopColor="rgb(5 11 18)" stopOpacity="0.9" />
          </radialGradient>
        </defs>

        <rect width="1000" height="600" fill="url(#lp-grid)" />

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
              strokeOpacity="0.25"
              strokeWidth="1"
              className="lp-data-flow"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          );
        })}

        {VEHICLE_PATHS.map(([a, b], i) => {
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
              transition={{
                duration: 6 + i,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 1.3,
              }}
            />
          );
        })}

        {NODES.map((node, i) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="10" fill="rgb(22 136 255)" opacity="0.08" />
            <motion.circle
              cx={node.x}
              cy={node.y}
              r="3"
              fill="rgb(46 168 255)"
              initial={{ opacity: 0.4 }}
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2.6, repeat: Infinity, delay: i * 0.25, ease: "easeInOut" }}
            />
          </g>
        ))}

        <rect width="1000" height="600" fill="url(#lp-vignette)" />
      </svg>
    </div>
  );
}
