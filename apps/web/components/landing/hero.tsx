"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { useAuth } from "@/lib/auth-context";

import { FloatingIntelCards } from "./floating-intel-cards";
import { HeroNetworkBackground } from "./hero-network-background";

export function Hero() {
  const { user } = useAuth();

  return (
    <section className="relative flex min-h-screen items-center overflow-hidden pt-24">
      <HeroNetworkBackground />
      <FloatingIntelCards />

      <div className="relative z-10 mx-auto w-full max-w-5xl px-4 text-center sm:px-6 lg:px-8">
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-6 text-xs font-semibold uppercase tracking-[0.3em] text-lp-secondary"
        >
          Operational Intelligence Platform
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-4xl font-bold leading-[1.05] tracking-tight text-lp-text-0 sm:text-6xl lg:text-7xl"
        >
          SEE THE SIGNAL.
          <br />
          <span className="bg-gradient-to-r from-lp-primary-2 to-lp-secondary bg-clip-text text-transparent">
            UNDERSTAND THE MOVEMENT.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
          className="mx-auto mt-7 max-w-2xl text-base leading-relaxed text-lp-text-1 sm:text-lg"
        >
          GP Sentinel transforms distributed camera infrastructure into real-time
          operational intelligence — connecting live video, AI vision, tracking,
          ANPR, alerts and evidence through one secure, permission-aware platform.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
        >
          <Link
            href={user ? "/trace" : "/login"}
            className="group inline-flex items-center gap-2 rounded bg-lp-primary px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-white shadow-[0_0_40px_-8px_rgba(22,136,255,0.6)] transition-all hover:bg-lp-primary-2 hover:shadow-[0_0_50px_-6px_rgba(46,168,255,0.75)]"
          >
            Enter GP Sentinel
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
          <a
            href="#platform"
            className="rounded border border-lp-border px-7 py-3.5 text-sm font-semibold uppercase tracking-wider text-lp-text-1 transition-colors hover:border-lp-primary/50 hover:text-lp-text-0"
          >
            Explore Platform
          </a>
        </motion.div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-lp-bg-0 to-transparent" />
    </section>
  );
}
