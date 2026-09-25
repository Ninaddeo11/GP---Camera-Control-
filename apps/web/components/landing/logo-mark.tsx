interface LogoMarkProps {
  className?: string;
  size?: number;
}

/** A geometric shield/aperture mark — no external image asset. Reused by
 * the nav, footer, and app/icon.tsx (favicon). */
export function LogoMark({ className, size = 28 }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M16 2 L28 7 V16 C28 23.5 22.8 28.5 16 30 C9.2 28.5 4 23.5 4 16 V7 Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="7" stroke="currentColor" strokeWidth="1.3" />
      <circle cx="16" cy="16" r="2.6" fill="currentColor" />
      <path d="M16 9 V6.2 M16 26 V23 M9 16 H6.2 M25.8 16 H23" stroke="currentColor" strokeWidth="1.1" />
    </svg>
  );
}
