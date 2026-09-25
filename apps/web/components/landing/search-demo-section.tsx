"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { Reveal } from "./reveal";

const DEMO_PLATE = "MH12AB1234";
const DEMO_RESULT = {
  title: "Vehicle Track #18492",
  fields: [
    { label: "First Seen", value: "CAM-021" },
    { label: "Last Seen", value: "CAM-048" },
    { label: "Cameras", value: "3" },
    { label: "Events", value: "7" },
    { label: "Jurisdictions", value: "2" },
  ],
};

/**
 * Entirely client-side and hardcoded — this never calls the real
 * /api/tracking endpoint. It demonstrates what the authenticated Vehicle
 * Intelligence view looks like without exposing any real search
 * capability or data on the public site (brief section 3: "All visual
 * data on the public landing page must be illustrative / simulated").
 */
export function SearchDemoSection() {
  const [query, setQuery] = useState("");
  const matched = query.trim().toUpperCase() === DEMO_PLATE;

  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-2xl px-4 text-center sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="text-2xl font-bold tracking-tight text-lp-text-0 sm:text-3xl">
            Not just a video viewer. An intelligence platform.
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-10">
            <label htmlFor="search-demo" className="sr-only">
              Try the demo search
            </label>
            <input
              id="search-demo"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search cameras, vehicles, plates, events… try "${DEMO_PLATE}"`}
              className="w-full rounded border border-lp-border bg-lp-bg-1 px-5 py-3.5 text-center font-mono text-sm text-lp-text-0 placeholder:text-lp-text-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
            />

            <AnimatePresence>
              {matched && (
                <motion.div
                  initial={{ opacity: 0, y: 10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                  className="mt-5 overflow-hidden rounded border border-lp-primary/30 bg-lp-bg-1/70 p-5 text-left"
                >
                  <div className="text-sm font-semibold text-lp-text-0">{DEMO_RESULT.title}</div>
                  <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
                    {DEMO_RESULT.fields.map((f) => (
                      <div key={f.label}>
                        <dt className="text-[10px] uppercase tracking-wider text-lp-text-2">{f.label}</dt>
                        <dd className="mt-1 font-mono text-sm text-lp-text-0">{f.value}</dd>
                      </div>
                    ))}
                  </dl>
                </motion.div>
              )}
            </AnimatePresence>

            <p className="mt-4 text-[11px] text-lp-text-2">Illustrative demo — not a live search.</p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
