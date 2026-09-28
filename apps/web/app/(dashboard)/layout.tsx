"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useDialogFocus } from "@/lib/use-dialog-focus";
import { NavSidebar } from "@/components/nav-sidebar";
import { TopBar } from "@/components/top-bar";
import { useAuth } from "@/lib/auth-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div
      onKeyDown={(e) => {
        if (e.key === "Escape") setMenuOpen(false);
      }}
      className="flex h-dvh overflow-hidden bg-background"
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:z-[3000] focus:rounded focus:bg-surface focus:p-3"
      >
        Skip to workspace
      </a>
      <div className="hidden md:block">
        <NavSidebar />
      </div>
      {menuOpen && <NavigationDrawer onClose={() => setMenuOpen(false)} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMenuOpen(true)} />
        <main
          id="main-content"
          className="min-w-0 flex-1 overflow-y-auto p-3 md:p-5"
        >
          {children}
        </main>
      </div>
    </div>
  );
}

function NavigationDrawer({ onClose }: { onClose: () => void }) {
  const ref = useDialogFocus(onClose);
  return (
    <div
      ref={ref}
      role="dialog"
      aria-modal="true"
      aria-label="Navigation"
      className="fixed inset-0 z-[2000] flex md:hidden"
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-background/80"
        onClick={onClose}
      />
      <div className="relative h-full">
        <button
          className="absolute right-3 top-2 text-muted"
          aria-label="Close navigation"
          onClick={onClose}
        >
          ?
        </button>
        <NavSidebar onNavigate={onClose} />
      </div>
    </div>
  );
}
