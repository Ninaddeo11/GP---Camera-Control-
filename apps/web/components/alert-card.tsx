"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { WatchlistMatchOut, WatchlistPriority } from "@/lib/types";

const PRIORITY_TONE: Record<WatchlistPriority, "neutral" | "warning" | "danger"> = {
  low: "neutral",
  medium: "neutral",
  high: "warning",
  critical: "danger",
};

interface AlertCardProps {
  alert: WatchlistMatchOut;
  onAcknowledge: (id: string) => void;
  acknowledging: boolean;
}

export function AlertCard({ alert, onAcknowledge, acknowledging }: AlertCardProps) {
  return (
    <div
      className={cn(
        "rounded border border-border p-3",
        !alert.acknowledged && "animate-alert-pulse border-danger/40"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-foreground">{alert.watchlist_plate_text}</div>
          <div className="text-xs text-muted">
            matched at {alert.camera_name} · {new Date(alert.wall_ts).toLocaleString()}
          </div>
        </div>
        <Badge tone={PRIORITY_TONE[alert.priority]}>{alert.priority}</Badge>
      </div>

      {alert.reason && <p className="mt-2 text-xs text-muted">{alert.reason}</p>}

      {alert.snapshot_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={alert.snapshot_url}
          alt={`Snapshot of ${alert.matched_plate_text} at ${alert.camera_name}`}
          className="mt-2 h-24 w-full rounded object-cover"
        />
      )}

      <div className="mt-3 flex items-center justify-between">
        {alert.acknowledged ? (
          <Badge tone="success">
            Acknowledged{alert.acknowledged_by_username ? ` by ${alert.acknowledged_by_username}` : ""}
          </Badge>
        ) : (
          <Badge tone="danger">Unacknowledged</Badge>
        )}
        {!alert.acknowledged && (
          <Button size="sm" variant="secondary" disabled={acknowledging} onClick={() => onAcknowledge(alert.id)}>
            {acknowledging ? "Acknowledging…" : "Acknowledge"}
          </Button>
        )}
      </div>
    </div>
  );
}
