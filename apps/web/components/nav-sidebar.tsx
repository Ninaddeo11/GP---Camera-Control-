"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

interface NavItem {
  href: string;
  label: string;
  /** Omit to show for every authenticated user regardless of permission. */
  requiresPermission?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/video-wall", label: "Video Wall", requiresPermission: "camera:read" },
  { href: "/registry", label: "Registry Map", requiresPermission: "camera:read" },
  { href: "/trace", label: "Vehicle Trace", requiresPermission: "vehicle_trace:read" },
  { href: "/watchlist", label: "Watchlist & Alerts", requiresPermission: "watchlist:read" },
  { href: "/audit", label: "Audit Log", requiresPermission: "audit_log:read" },
];

/**
 * Every item is gated on the logged-in user's actual permissions — a
 * constable simply never sees "Watchlist & Alerts" in their nav, rather
 * than seeing it and hitting a 403. This is the RBAC demonstration the
 * project brief asks for: it shows up by using the product normally, not
 * as a dedicated "look, RBAC works" screen.
 */
export function NavSidebar() {
  const pathname = usePathname();
  const { hasPermission } = useAuth();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.requiresPermission || hasPermission(item.requiresPermission)
  );

  return (
    <nav className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface px-3 py-4">
      <div className="mb-6 px-2 text-sm font-semibold tracking-tight text-foreground">
        Sentinel Grid
      </div>
      <ul className="flex flex-col gap-1">
        {visibleItems.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={cn(
                  "block rounded px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent/10 text-accent"
                    : "text-muted hover:bg-surface-muted hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
