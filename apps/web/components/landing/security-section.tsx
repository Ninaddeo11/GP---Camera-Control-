"use client";

import { Reveal } from "./reveal";

// Factual, non-exaggerated language only — no "military-grade", "100%
// secure", "zero false positives", or "fully compliant" claims (brief
// section 17 / 33). Each concept maps to something actually built:
// security/rbac.py (RBAC + jurisdiction), services/audit_service.py
// (hash-chained audit log), services/evidence_export.py (SHA-256
// chain-of-custody).
const CONCEPTS = [
  "Role-based access",
  "Jurisdiction-aware access",
  "Audit trails",
  "Evidence control",
  "Secure streaming",
  "Data retention",
  "Operational visibility",
];

export function SecuritySection() {
  return (
    <section id="security" className="border-y border-lp-border bg-lp-bg-1/40 py-24 sm:py-32">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-lp-text-0 sm:text-5xl">
            INTELLIGENCE
            <br />
            <span className="text-lp-primary-2">WITHOUT LOSING CONTROL.</span>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-14 flex flex-wrap justify-center gap-3">
            {CONCEPTS.map((concept) => (
              <span
                key={concept}
                className="rounded-full border border-lp-border px-5 py-2.5 text-xs font-medium uppercase tracking-wider text-lp-text-1"
              >
                {concept}
              </span>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
