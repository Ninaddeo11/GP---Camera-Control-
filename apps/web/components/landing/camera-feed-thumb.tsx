"use client";

// Renders a "camera feed" look by zooming into a different region of the
// one licensed hero photo (see hero-city-background.tsx) via
// background-position — not a second, third, fourth... stock photo per
// panel. Every "camera" on this page is honestly the same real city photo
// seen from a different framing, which is both cheaper to license
// correctly and visually consistent (they all plausibly belong to the
// same real place) than mismatched stock photos from different cities
// would be.
export function CameraFeedThumb({
  className,
  focusX,
  focusY,
  zoom = 260,
}: {
  className?: string;
  /** Background-position percentages (0-100) into the source photo. */
  focusX: number;
  focusY: number;
  /** background-size percentage — higher zooms further into the source photo. */
  zoom?: number;
}) {
  return (
    <div
      aria-hidden="true"
      className={className}
      style={{
        backgroundImage: "url(/images/hero-city-desktop.webp)",
        backgroundSize: `${zoom}% auto`,
        backgroundPosition: `${focusX}% ${focusY}%`,
        backgroundRepeat: "no-repeat",
      }}
    />
  );
}
