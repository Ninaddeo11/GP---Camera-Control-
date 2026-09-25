"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { LogoMark } from "@/components/landing/logo-mark";
import { ApiRequestError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

// useSearchParams() (used here just to show a "password reset" success
// banner after a redirect from /reset-password) requires a Suspense
// boundary in the App Router, even in a client component, or `next build`
// fails static prerendering for this route.
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

// The "secure counterpart" of the landing page (brief section 21) — same
// dark .landing-page palette, and a visual nod to what login actually does
// (identity → role → jurisdiction → permissions, per security/rbac.py),
// without literally delaying a real login behind a multi-second staged
// animation just for effect.
const VERIFICATION_STEPS = ["Identity", "Role", "Jurisdiction", "Access policy"];

function LoginForm() {
  const { login } = useAuth();
  const searchParams = useSearchParams();
  const justReset = searchParams.get("reset") === "success";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Unable to sign in. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="landing-page flex min-h-screen items-center justify-center px-4 py-16">
      <div className="grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded border border-lp-border lg:grid-cols-2">
        <div className="hidden flex-col justify-between bg-lp-bg-1/60 p-10 lg:flex">
          <Link href="/" className="flex items-center gap-2 text-lp-text-0">
            <LogoMark className="text-lp-primary-2" />
            <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
          </Link>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lp-text-2">Secure access</p>
            <ol className="mt-4 space-y-3">
              {VERIFICATION_STEPS.map((step, i) => (
                <li key={step} className="flex items-center gap-3 text-sm">
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full border text-[10px] ${
                      submitting
                        ? "border-lp-primary bg-lp-primary/20 text-lp-primary-2"
                        : "border-lp-border text-lp-text-2"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span className={submitting ? "text-lp-text-0" : "text-lp-text-2"}>{step} verified</span>
                </li>
              ))}
            </ol>
          </div>

          <p className="text-xs text-lp-text-2">
            Every request is resolved against role, jurisdiction and permission —
            server-side, on every request.
          </p>
        </div>

        <div className="bg-lp-bg-0 p-8 sm:p-10">
          <div className="mb-8 lg:hidden">
            <Link href="/" className="flex items-center gap-2 text-lp-text-0">
              <LogoMark className="text-lp-primary-2" />
              <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
            </Link>
          </div>

          <h1 className="text-lg font-semibold text-lp-text-0">Sign in</h1>
          <p className="mt-1 text-xs text-lp-text-2">Sign in with your department credentials.</p>

          {justReset && (
            <p className="mt-4 rounded border border-lp-success/30 bg-lp-success/10 px-3 py-2 text-xs text-lp-success">
              Password reset — sign in with your new password.
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="username" className="text-xs font-medium text-lp-text-2">
                Username
              </label>
              <input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="h-10 rounded border border-lp-border bg-lp-bg-1 px-3 text-sm text-lp-text-0 placeholder:text-lp-text-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-medium text-lp-text-2">
                  Password
                </label>
                <Link href="/forgot-password" className="text-xs text-lp-primary-2 underline">
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-10 rounded border border-lp-border bg-lp-bg-1 px-3 text-sm text-lp-text-0 placeholder:text-lp-text-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
              />
            </div>
            {error && (
              <p role="alert" className="text-xs text-lp-alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="mt-2 h-11 rounded bg-lp-primary text-sm font-semibold uppercase tracking-wider text-white transition-colors hover:bg-lp-primary-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Verifying…" : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-lp-text-2">
            No account?{" "}
            <Link href="/request-access" className="text-lp-primary-2 underline">
              Request access
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
