import type { Metadata } from "next";
import Link from "next/link";

import { LogoMark } from "@/components/landing/logo-mark";

export const metadata: Metadata = {
  title: "Request Access",
};

/**
 * There is no self-service account creation in this system — accounts are
 * provisioned by department administrators against a specific rank and
 * jurisdiction (see README.md "RBAC model"). Per the landing-page brief's
 * own instruction ("Do not fake functionality where real functionality
 * doesn't exist... Do not create fake authentication"), this is a plain
 * informational page, not a form that pretends to submit somewhere real.
 */
export default function RequestAccessPage() {
  return (
    <div className="landing-page flex min-h-screen flex-col items-center justify-center px-4 py-20 text-center">
      <Link href="/" className="mb-8 flex items-center gap-2 text-lp-text-0">
        <LogoMark className="text-lp-primary-2" />
        <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
      </Link>

      <div className="max-w-md rounded border border-lp-border bg-lp-bg-1/50 p-8">
        <h1 className="text-xl font-semibold text-lp-text-0">Requesting access</h1>
        <p className="mt-4 text-sm leading-relaxed text-lp-text-1">
          GP Sentinel accounts are provisioned by department administrators against a
          specific rank tier and jurisdiction — there is no self-service sign-up. If
          you already hold departmental credentials, sign in directly. Otherwise,
          contact your department&apos;s system administrator to have an account
          created for you.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-flex items-center gap-2 rounded bg-lp-primary px-6 py-3 text-xs font-semibold uppercase tracking-wider text-white transition-colors hover:bg-lp-primary-2"
        >
          Go to sign in →
        </Link>
      </div>

      <Link href="/" className="mt-8 text-xs text-lp-text-2 underline">
        Back to home
      </Link>
    </div>
  );
}
