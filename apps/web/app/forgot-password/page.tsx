"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { LogoMark } from "@/components/landing/logo-mark";
import { apiFetch, ApiRequestError } from "@/lib/api-client";

interface ForgotPasswordResponse {
  detail: string;
  dev_reset_token?: string;
}

export default function ForgotPasswordPage() {
  const [username, setUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ForgotPasswordResponse | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const resp = await apiFetch<ForgotPasswordResponse>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ username }),
      });
      setResult(resp);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Something went wrong.");
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

        <h1 className="text-base font-semibold text-lp-text-0">Reset your password</h1>
        <p className="mt-1 text-xs text-lp-text-2">
          Enter your username and, if the account exists, reset instructions will be issued.
        </p>

        {result ? (
          <div className="mt-6 flex flex-col gap-3">
            <p className="text-sm text-lp-text-1">{result.detail}</p>
            {result.dev_reset_token && (
              <div className="rounded border border-lp-warning/30 bg-lp-warning/10 p-3 text-xs text-lp-text-1">
                <p className="font-medium text-lp-warning">
                  Dev mode — no email is configured, so the reset token is shown here directly.
                </p>
                <p className="mt-2 break-all font-mono text-lp-text-0">{result.dev_reset_token}</p>
                <Link
                  href={`/reset-password?token=${encodeURIComponent(result.dev_reset_token)}`}
                  className="mt-2 inline-block text-lp-primary-2 underline"
                >
                  Continue to reset password →
                </Link>
              </div>
            )}
            <Link href="/login" className="text-xs text-lp-primary-2 underline">
              Back to sign in
            </Link>
          </div>
        ) : (
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
              {submitting ? "Submitting…" : "Send reset instructions"}
            </button>
            <Link href="/login" className="text-center text-xs text-lp-text-2 underline">
              Back to sign in
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
