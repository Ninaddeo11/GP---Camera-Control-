"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth-context";

import { Reveal } from "./reveal";

export function CtaSection() {
  const { user } = useAuth();

  return (
    <section id="about" className="relative overflow-hidden py-28">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-lp-primary/5 to-transparent" />
      <div className="relative mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="text-3xl font-bold leading-tight tracking-tight text-lp-text-0 sm:text-5xl">
            TURN CAMERA DATA INTO
            <br />
            <span className="text-lp-primary-2">OPERATIONAL INTELLIGENCE.</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base text-lp-text-1">
            One platform for video, vision, tracking, ANPR, events, evidence and
            command.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href={user ? "/trace" : "/login"}
              className="group inline-flex items-center gap-2 rounded bg-lp-primary px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-white shadow-[0_0_40px_-8px_rgba(22,136,255,0.6)] transition-all hover:bg-lp-primary-2"
            >
              Enter GP Sentinel
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
            {!user && (
              <Link
                href="/request-access"
                className="rounded border border-lp-border px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-lp-text-1 transition-colors hover:border-lp-primary/50 hover:text-lp-text-0"
              >
                Request Access
              </Link>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
