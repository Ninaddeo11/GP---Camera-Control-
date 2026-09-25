"use client";

import type { ApiError } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://localhost/api";

const ACCESS_TOKEN_KEY = "sentinelgrid.access_token";
const REFRESH_TOKEN_KEY = "sentinelgrid.refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(status: number, body: ApiError) {
    super(body.detail);
    this.status = status;
    this.code = body.code;
  }
}

// The backend now rotates the refresh token on every use (see
// services/api/api/auth.py) and treats an already-used refresh token
// being presented again as a theft/replay signal, revoking every session
// for the account. Two concurrent requests that both hit a 401 at nearly
// the same moment would otherwise each try to refresh independently — the
// second one arriving at the backend with a refresh token the first one
// already rotated away, triggering exactly that revocation by accident.
// This module-level in-flight guard makes every concurrent caller share
// one refresh call instead.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;

    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) {
      clearTokens();
      return null;
    }
    const data = await resp.json();
    setTokens(data.access_token, data.refresh_token);
    return data.access_token as string;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/**
 * Fetch wrapper attaching the bearer token and retrying exactly once after
 * a silent token refresh on a 401 — anything else (403, 404, ...) is
 * surfaced as-is so callers can show the backend's own {detail, code}.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}, _retried = false): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401 && !_retried) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, options, true);
    }
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiRequestError(401, { detail: "Not authenticated", code: "unauthorized" });
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  const body = await resp.json().catch(() => ({ detail: resp.statusText, code: "error" }));

  if (!resp.ok) {
    throw new ApiRequestError(resp.status, body as ApiError);
  }

  return body as T;
}

export function apiBaseUrl(): string {
  return API_BASE;
}
