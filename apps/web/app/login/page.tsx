"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
    <div className="flex min-h-screen items-center justify-center bg-surface-muted px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-base">Sentinel Grid</CardTitle>
          <p className="mt-1 text-xs text-muted">Sign in with your department credentials</p>
        </CardHeader>
        <CardContent>
          {justReset && (
            <p className="mb-4 rounded border border-success/30 bg-success/10 px-3 py-2 text-xs text-success">
              Password reset — sign in with your new password.
            </p>
          )}
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
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-medium text-muted">
                  Password
                </label>
                <Link href="/forgot-password" className="text-xs text-accent underline">
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && (
              <p role="alert" className="text-xs text-danger">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting} className="mt-2 w-full">
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
