"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";
export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { user, logout, hasPermission } = useAuth();
  const [query, setQuery] = useState("");
  const router = useRouter();
  if (!user) return null;
  return (
    <header className="flex min-h-16 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border bg-surface/90 px-4 py-3">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <a
          href={hasPermission("camera:read") ? "/registry" : "/trace"}
          className="flex items-center gap-2 text-sm font-semibold md:hidden"
        >
          <span className="grid h-7 w-7 place-items-center rounded bg-accent text-white">
            S
          </span>
          Sentinel Grid
        </a>
        <Button
          variant="ghost"
          onClick={onMenu}
          aria-label="Open navigation"
          className="md:hidden"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </Button>
        {hasPermission("camera:read") && (
          <form
            className="hidden items-center gap-2 sm:flex"
            onSubmit={(e) => {
              e.preventDefault();
              window.location.assign(
                `/registry?q=${encodeURIComponent(query)}`,
              );
            }}
          >
            <Input
              aria-label="Global camera search"
              placeholder="Search cameras, locations…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-52 lg:w-64"
            />
            <Button size="sm" variant="secondary" type="submit">
              Search
            </Button>
          </form>
        )}
        <select
          aria-label="Command workspace"
          className="max-w-44 text-xs"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) router.push(e.target.value);
          }}
        >
          <option value="" disabled>
            {user.role_code} · Command
          </option>
          {hasPermission("camera:read") && (
            <>
              <option value="/video-wall">Video Wall</option>
              <option value="/registry">Registry Map</option>
            </>
          )}
          {hasPermission("vehicle_trace:read") && (
            <option value="/trace">Vehicle Trace</option>
          )}
          {hasPermission("watchlist:read") && (
            <option value="/watchlist">Watchlist & Alerts</option>
          )}
          {hasPermission("audit_log:read") && (
            <option value="/audit">Audit Log</option>
          )}
        </select>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden text-right xl:block">
          <div className="text-xs text-foreground">
            {user.jurisdictions.map((j) => j.name).join(", ") ||
              "No jurisdiction assigned"}
          </div>
          <div className="text-xs text-muted">
            {user.department || user.role_name}
          </div>
        </div>
        <Badge tone="accent">{user.role_code}</Badge>
        <div className="hidden text-right sm:block">
          <div className="text-sm font-medium">{user.full_name}</div>
          <div className="text-xs text-muted">{user.username}</div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void logout()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
