"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
    <div className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-base">Set a new password</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="reset-token" className="text-xs font-medium text-muted">
                Reset token
              </label>
              <Input
                id="reset-token"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="new-password" className="text-xs font-medium text-muted">
                New password
              </label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="confirm-password" className="text-xs font-medium text-muted">
                Confirm new password
              </label>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && (
              <p role="alert" className="text-xs text-danger">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Resetting…" : "Reset password"}
            </Button>
            <p className="text-center text-xs text-muted">
              This will sign you out everywhere else too.{" "}
              <Link href="/login" className="text-accent underline">
                Back to sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
