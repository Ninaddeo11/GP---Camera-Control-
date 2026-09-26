"use client";

import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

import { LogoMark } from "./logo-mark";

const NAV_LINKS = [
  { href: "#platform", label: "Platform" },
  { href: "#intelligence", label: "Intelligence" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#security", label: "Security" },
  { href: "#about", label: "About" },
];

export function LandingNav() {
  const { user } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (latest) => {
    setScrolled(latest > 24);
  });

  return (
    <motion.header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-[padding,background-color,border-color] duration-300",
        scrolled
          ? "border-b border-lp-border bg-lp-bg-0/85 py-2.5 backdrop-blur-md"
          : "border-b border-transparent bg-transparent py-5"
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 text-lp-text-0">
          <LogoMark className="text-lp-primary-2" />
          <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-xs font-medium uppercase tracking-wider text-lp-text-2 transition-colors hover:text-lp-text-0"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-4 md:flex">
          <Link
            href={user ? "/trace" : "/login"}
            aria-label={user ? "Search" : "Search (sign in required)"}
            className="flex h-8 w-8 items-center justify-center rounded text-lp-text-2 transition-colors hover:text-lp-text-0"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
          </Link>

          {user ? (
            <Link
              href="/trace"
              className="rounded border border-lp-primary/40 bg-lp-primary/10 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-lp-primary-2 transition-colors hover:bg-lp-primary/20"
            >
              Enter GP Sentinel →
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="text-xs font-semibold uppercase tracking-wider text-lp-text-1 transition-colors hover:text-lp-text-0"
              >
                Login
              </Link>
              <Link
                href="/request-access"
                className="rounded border border-lp-primary/40 bg-lp-primary/10 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-lp-primary-2 transition-colors hover:bg-lp-primary/20"
              >
                Request Access
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded border border-lp-border text-lp-text-0 md:hidden"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          <span className="sr-only">Toggle navigation</span>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            {mobileOpen ? (
              <path d="M3 3 L15 15 M15 3 L3 15" stroke="currentColor" strokeWidth="1.5" />
            ) : (
              <path d="M2 5 H16 M2 9 H16 M2 13 H16" stroke="currentColor" strokeWidth="1.5" />
            )}
          </svg>
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-lp-border bg-lp-bg-0/95 px-4 py-4 backdrop-blur-md md:hidden">
          <nav className="flex flex-col gap-4" aria-label="Primary mobile">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="text-sm font-medium uppercase tracking-wider text-lp-text-1"
              >
                {link.label}
              </a>
            ))}
            <div className="mt-2 flex flex-col gap-3 border-t border-lp-border pt-4">
              {user ? (
                <Link href="/trace" className="text-sm font-semibold text-lp-primary-2">
                  Enter GP Sentinel →
                </Link>
              ) : (
                <>
                  <Link href="/login" className="text-sm font-semibold text-lp-text-0">
                    Login
                  </Link>
                  <Link href="/request-access" className="text-sm font-semibold text-lp-primary-2">
                    Request Access
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </motion.header>
  );
}
