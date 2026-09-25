"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export function TopBar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  const firstJurisdiction = user.jurisdictions[0];
  const jurisdictionLabel =
    user.jurisdictions.length === 0 || !firstJurisdiction
      ? "No jurisdiction assigned"
      : user.jurisdictions.length === 1
        ? firstJurisdiction.name
        : `${firstJurisdiction.name} +${user.jurisdictions.length - 1} more`;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <div />
      <div className="flex items-center gap-3">
        <Badge tone="accent">{user.role_code} · {user.role_name}</Badge>
        <Badge tone="neutral" title={user.jurisdictions.map((j) => j.name).join(", ")}>
          {jurisdictionLabel}
        </Badge>
        <div className="ml-2 text-right">
          <div className="text-sm font-medium text-foreground">{user.full_name}</div>
          <div className="text-xs text-muted">{user.department || user.username}</div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void logout()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
