"use client";

import { Reveal } from "./reveal";

const ROLES = [
  {
    title: "Command",
    items: ["Strategic overview", "Cross-region intelligence", "Network visibility"],
  },
  {
    title: "Operations",
    items: ["Live monitoring", "Operational oversight", "Alerts and events"],
  },
  {
    title: "Field",
    items: ["Assigned cameras", "Nearby events", "Vehicle intelligence", "Field operations"],
  },
  {
    title: "Infrastructure",
    items: ["Camera health", "Streams", "Inference", "Platform services"],
  },
];

export function RolesSection() {
  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            INTELLIGENCE,
            <br />
            <span className="text-lp-primary-2">DELIVERED WITH CONTEXT.</span>
          </h2>
          <p className="mt-5 text-base text-lp-text-1">
            Every user sees what they are authorized to see, shaped by their role
            and the environment they are responsible for.
          </p>
        </Reveal>

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((role, i) => (
            <Reveal key={role.title} delay={i * 0.08}>
              <div className="h-full rounded border border-lp-border bg-lp-bg-1/50 p-6">
                <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-lp-primary-2">
                  {role.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {role.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-lp-text-1">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-lp-text-2" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
