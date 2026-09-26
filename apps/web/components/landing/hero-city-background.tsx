"use client";

// Real aerial nighttime city photography, not an abstract SVG network —
// see README.md "Public landing page" section for the licensing note.
// Photo: Dohyuk You, Dubai highway interchange at night, Unsplash License
// (free for commercial use). Downloaded and re-encoded to WebP at
// apps/web/public/images/hero-city-{desktop,mobile}.webp rather than
// hotlinked, so the page doesn't depend on a third-party CDN staying up.
// This is a placeholder licensed photo, not custom-shot footage of any
// real deployment — swap for owned/licensed footage before production if
// that matters for your brand.

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import Image from "next/image";
import { type PointerEvent as ReactPointerEvent } from "react";

interface CameraNode {
  id: string;
  leftPct: number;
  topPct: number;
}

// Hand-placed near visible road lines in the photo itself, not scattered
// randomly — brief section 15: "avoid turning the city into a spiderweb",
// only a handful of nodes. Also hand-checked against
// hero-intelligence-overlay.tsx's panel positions (a separate coordinate
// system, in plain Tailwind percentages) so a node's pulse circle never
// renders underneath a floating panel — that collision is exactly what
// produced a stray dark smudge behind the first camera panel before this
// comment was written; keep the two files' reserved regions in sync if
// either changes:
//   left column (headline/body/buttons): x 0-40%
//   CAM-021 panel:  x 54-70%,  y 14-24%
//   CAM-048 panel:  x 76-90%,  y 40-50%
//   detection box:  x 52-58%,  y 44-50%
//   tracking card:  x 58-75%,  y 54-64%
//   plate panel:    x 74-94%,  y 76-88%
//   alert panel:    x 76-92%,  y 16-24%
//
// Path/node coordinates use a 1000x600 viewBox — the same coordinate
// convention multi-camera-section.tsx uses for its own SVG paths, kept
// consistent across the page's hand-authored vector overlays.
const CAMERA_NODES: readonly CameraNode[] = [
  { id: "cam-a", leftPct: 46, topPct: 30 },
  { id: "cam-b", leftPct: 62, topPct: 34 },
  { id: "cam-c", leftPct: 86, topPct: 63 },
];

// One continuous curve traced over the real highway interchange visible
// in the photo (not a random line through buildings, per brief section
// 11) — authored in the same 1000x600 viewBox space used by the other
// landing sections (living-network-section.tsx, multi-camera-section.tsx)
// for a consistent coordinate convention across the page.
export const VEHICLE_PATH = "M 140 430 C 300 400, 380 300, 540 290 C 660 282, 720 340, 860 260";

interface HeroCityBackgroundProps {
  /** Which camera node is the current story beat's focus (0..N-1). */
  activeNodeIndex: number;
}

export function HeroCityBackground({ activeNodeIndex }: HeroCityBackgroundProps) {
  const prefersReducedMotion = useReducedMotion();

  // Very subtle multi-depth parallax (brief section 17/18): the photo
  // itself drifts least, the SVG intelligence layer on top of it drifts
  // more — two depth groups is enough to read as depth without the
  // "6 independently-tuned parallax layers" the brief itself calls out
  // as more literal fidelity than this pass attempts.
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const springX = useSpring(pointerX, { stiffness: 45, damping: 20 });
  const springY = useSpring(pointerY, { stiffness: 45, damping: 20 });
  const cityX = useTransform(springX, (v) => v * 5);
  const cityY = useTransform(springY, (v) => v * 5);
  const overlayX = useTransform(springX, (v) => v * 10);
  const overlayY = useTransform(springY, (v) => v * 10);

  function handlePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (prefersReducedMotion) return;
    const rect = event.currentTarget.getBoundingClientRect();
    pointerX.set((event.clientX - rect.left) / rect.width - 0.5);
    pointerY.set((event.clientY - rect.top) / rect.height - 0.5);
  }

  return (
    <div className="absolute inset-0 overflow-hidden bg-lp-bg-00" onPointerMove={handlePointerMove}>
      <motion.div className="absolute inset-0" style={prefersReducedMotion ? undefined : { x: cityX, y: cityY }}>
        <Image
          src="/images/hero-city-desktop.webp"
          alt=""
          fill
          priority
          sizes="100vw"
          className="hidden object-cover object-center sm:block"
        />
        <Image
          src="/images/hero-city-mobile.webp"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover object-center sm:hidden"
        />
      </motion.div>

      {/* Cinematic treatment (brief section 3): dark gradient + blue tint +
          vignette — strong enough for the left-side text to stay readable,
          restrained enough that the city is still clearly visible, not a
          near-black background with a photo barely showing through. */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-lp-bg-00 via-lp-bg-00/65 to-lp-bg-00/15" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-lp-bg-00/85 via-transparent to-lp-bg-00/50" />
      <div className="pointer-events-none absolute inset-0 bg-lp-primary/[0.06] mix-blend-overlay" />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "radial-gradient(ellipse at 65% 45%, transparent 35%, rgb(3 7 13 / 0.55) 100%)" }}
      />

      {/* Camera nodes + vehicle path, hidden below `sm` along with the
          floating panels (hero-intelligence-overlay.tsx) — brief section
          34: mobile is city -> hero text -> vehicle -> detection ->
          intelligence as separate scroll beats, not everything overlapping
          the text at once. On a narrow viewport there's no separate
          "right side" for this layer to occupy without colliding with the
          headline (confirmed by screenshotting: a node rendered directly
          on top of the eyebrow text). */}
      <motion.div
        className="absolute inset-0 hidden sm:block"
        style={prefersReducedMotion ? undefined : { x: overlayX, y: overlayY }}
      >
        <svg viewBox="0 0 1000 600" preserveAspectRatio="xMidYMid slice" className="h-full w-full" aria-hidden="true">
          <path
            d={VEHICLE_PATH}
            fill="none"
            stroke="rgb(46 168 255)"
            strokeWidth="2"
            strokeDasharray="3 7"
            opacity="0.55"
          />
          {!prefersReducedMotion && (
            <motion.circle
              r="4.5"
              fill="#FFFFFF"
              stroke="rgb(46 168 255)"
              strokeWidth="3"
              animate={{ offsetDistance: ["0%", "100%"] }}
              transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
              style={{ offsetPath: `path('${VEHICLE_PATH}')` }}
            />
          )}

          {CAMERA_NODES.map((node, i) => {
            const isActive = i === activeNodeIndex;
            return (
              <g key={node.id} transform={`translate(${node.leftPct * 10} ${node.topPct * 6})`}>
                <circle r="16" fill="rgb(46 168 255)" opacity={isActive ? 0.22 : 0.07} />
                <circle
                  r="3.5"
                  fill={isActive ? "#FFFFFF" : "rgb(46 168 255)"}
                  className={isActive ? "lp-node-pulse" : undefined}
                />
              </g>
            );
          })}
        </svg>
      </motion.div>
    </div>
  );
}

export { CAMERA_NODES };
