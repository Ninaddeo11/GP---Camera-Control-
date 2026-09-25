import Link from "next/link";

import { LogoMark } from "./logo-mark";

const LINKS = [
  { href: "#platform", label: "Platform" },
  { href: "#intelligence", label: "Intelligence" },
  { href: "#security", label: "Security" },
  { href: "#architecture", label: "Architecture" },
  { href: "#about", label: "About" },
  { href: "/login", label: "Login" },
  { href: "/request-access", label: "Request Access" },
];

export function LandingFooter() {
  return (
    <footer className="border-t border-lp-border py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-10 sm:flex-row sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-lp-text-0">
              <LogoMark size={22} className="text-lp-primary-2" />
              <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
            </div>
            <p className="mt-3 max-w-xs text-sm text-lp-text-2">
              Camera Intelligence. Operational Context. Secure Control.
            </p>
          </div>

          <nav className="grid grid-cols-2 gap-x-10 gap-y-2 sm:grid-cols-1" aria-label="Footer">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-xs text-lp-text-2 transition-colors hover:text-lp-text-0"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="flex flex-col gap-2 text-xs text-lp-text-2">
            <span>Privacy</span>
            <span>Terms</span>
            <span>Security</span>
            <span>Contact</span>
          </div>
        </div>

        <div className="mt-12 border-t border-lp-border pt-6 text-xs text-lp-text-2">
          © 2026 GP Sentinel. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
