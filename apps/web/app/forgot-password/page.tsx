"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
    <div className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-base">Reset your password</CardTitle>
          <p className="mt-1 text-xs text-muted">
            Enter your username and, if the account exists, reset instructions will be issued.
          </p>
        </CardHeader>
        <CardContent>
          {result ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-foreground">{result.detail}</p>
              {result.dev_reset_token && (
                <div className="rounded border border-warning/30 bg-warning/10 p-3 text-xs text-foreground">
                  <p className="font-medium text-warning">
                    Dev mode — no email is configured, so the reset token is shown here directly.
                  </p>
                  <p className="mt-2 break-all font-mono">{result.dev_reset_token}</p>
                  <Link
                    href={`/reset-password?token=${encodeURIComponent(result.dev_reset_token)}`}
                    className="mt-2 inline-block text-accent underline"
                  >
                    Continue to reset password →
                  </Link>
                </div>
              )}
              <Link href="/login" className="text-xs text-accent underline">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="username" className="text-xs font-medium text-muted">
                  Username
                </label>
                <Input
                  id="username"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
              {error && (
                <p role="alert" className="text-xs text-danger">
                  {error}
                </p>
              )}
              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Submitting…" : "Send reset instructions"}
              </Button>
              <Link href="/login" className="text-center text-xs text-muted underline">
                Back to sign in
              </Link>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
