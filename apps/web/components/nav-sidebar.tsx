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
  {
    href: "/video-wall",
    label: "Video Wall",
    requiresPermission: "camera:read",
  },
  {
    href: "/registry",
    label: "Registry Map",
    requiresPermission: "camera:read",
  },
  {
    href: "/trace",
    label: "Vehicle Trace",
    requiresPermission: "vehicle_trace:read",
  },
  {
    href: "/watchlist",
    label: "Watchlist & Alerts",
    requiresPermission: "watchlist:read",
  },
  { href: "/audit", label: "Audit Log", requiresPermission: "audit_log:read" },
];

/**
 * Every item is gated on the logged-in user's actual permissions — a
 * constable simply never sees "Watchlist & Alerts" in their nav, rather
 * than seeing it and hitting a 403. This is the RBAC demonstration the
 * project brief asks for: it shows up by using the product normally, not
 * as a dedicated "look, RBAC works" screen.
 */
export function NavSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { hasPermission } = useAuth();

  const visibleItems = NAV_ITEMS.filter(
    (item) =>
      !item.requiresPermission || hasPermission(item.requiresPermission),
  );

  return (
    <nav
      aria-label="Main navigation"
      className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface px-3 py-5"
    >
      <div className="mb-6 px-2 text-sm font-semibold tracking-tight text-foreground">
        <span className="mr-2 inline-grid h-8 w-8 place-items-center rounded bg-accent text-white">
          S
        </span>
        Sentinel Grid
        <p className="mt-3 text-xs font-normal text-muted">
          Security command platform
        </p>
      </div>
      <ul className="flex flex-col gap-1">
        {visibleItems.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded border-l-2 px-3 py-3 text-sm font-medium transition-colors",
                  active
                    ? "border-accent bg-accent/20 text-foreground"
                    : "border-transparent text-muted hover:bg-surface-muted hover:text-foreground",
                )}
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  className="h-4 w-4 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                >
                  <path
                    d={
                      item.href === "/video-wall"
                        ? "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z"
                        : item.href === "/registry"
                          ? "M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3V3m6 3v15"
                          : item.href === "/trace"
                            ? "M4 5h10a5 5 0 010 10H9m-4-3-3 3 3 3m4-3H2"
                            : item.href === "/watchlist"
                              ? "M12 3l10 18H2L12 3zm0 6v5m0 3v1"
                              : "M6 3h12v18H6z m3 5h6m-6 4h6m-6 4h4"
                    }
                  />
                </svg>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
