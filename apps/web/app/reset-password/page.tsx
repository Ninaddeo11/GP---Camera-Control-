"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { LogoMark } from "@/components/landing/logo-mark";
import { apiFetch, ApiRequestError } from "@/lib/api-client";

// useSearchParams() requires a Suspense boundary in the App Router even in
// a client component, or `next build` fails static prerendering for this
// route — the inner component is the one that actually reads the query
// string; this file's default export just supplies that boundary.
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [resetToken, setResetToken] = useState(searchParams.get("token") ?? "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
      });
      router.push("/login?reset=success");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Reset failed — the link may have expired.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="landing-page flex min-h-screen items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm rounded border border-lp-border bg-lp-bg-1/50 p-8">
        <Link href="/" className="mb-6 flex items-center gap-2 text-lp-text-0">
          <LogoMark size={22} className="text-lp-primary-2" />
          <span className="text-sm font-semibold tracking-[0.2em]">GP SENTINEL</span>
        </Link>

        <h1 className="text-base font-semibold text-lp-text-0">Set a new password</h1>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="reset-token" className="text-xs font-medium text-lp-text-2">
              Reset token
            </label>
            <input
              id="reset-token"
              value={resetToken}
              onChange={(e) => setResetToken(e.target.value)}
              required
              className="h-10 rounded border border-lp-border bg-lp-bg-0 px-3 font-mono text-xs text-lp-text-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="new-password" className="text-xs font-medium text-lp-text-2">
              New password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              className="h-10 rounded border border-lp-border bg-lp-bg-0 px-3 text-sm text-lp-text-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="confirm-password" className="text-xs font-medium text-lp-text-2">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="h-10 rounded border border-lp-border bg-lp-bg-0 px-3 text-sm text-lp-text-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lp-primary-2"
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
            className="h-11 rounded bg-lp-primary text-sm font-semibold uppercase tracking-wider text-white transition-colors hover:bg-lp-primary-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Resetting…" : "Reset password"}
          </button>
          <p className="text-center text-xs text-lp-text-2">
            This will sign you out everywhere else too.{" "}
            <Link href="/login" className="text-lp-primary-2 underline">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
