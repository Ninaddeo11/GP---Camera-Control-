"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AlertCard } from "@/components/alert-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeadCell, TableRow } from "@/components/ui/table";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useAlertStream } from "@/lib/use-alert-stream";
import type { WatchlistEntryOut, WatchlistMatchOut, WatchlistPriority } from "@/lib/types";

const PRIORITIES: WatchlistPriority[] = ["low", "medium", "high", "critical"];

export default function WatchlistPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("watchlist:write");
  const canAcknowledge = hasPermission("alert:acknowledge");

  const [entries, setEntries] = useState<WatchlistEntryOut[]>([]);
  const [alerts, setAlerts] = useState<WatchlistMatchOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [newPlate, setNewPlate] = useState("");
  const [newReason, setNewReason] = useState("");
  const [newPriority, setNewPriority] = useState<WatchlistPriority>("medium");
  const [submitting, setSubmitting] = useState(false);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    try {
      setEntries(await apiFetch<WatchlistEntryOut[]>("/watchlist"));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to load watchlist.");
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      setAlerts(await apiFetch<WatchlistMatchOut[]>("/watchlist/matches?limit=100"));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to load alerts.");
    }
  }, []);

  useEffect(() => {
    void loadEntries();
    void loadAlerts();
  }, [loadEntries, loadAlerts]);

  useAlertStream(
    useCallback((incoming) => {
      setAlerts((prev) => {
        if (prev.some((a) => a.id === incoming.match_id)) return prev;
        return [
          {
            id: incoming.match_id,
            watchlist_id: incoming.watchlist_id,
            watchlist_plate_text: incoming.watchlist_plate_text,
            camera_id: incoming.camera_id,
            camera_name: incoming.camera_name,
            matched_plate_text: incoming.matched_plate_text,
            match_score: incoming.match_score,
            confidence: incoming.confidence,
            priority: incoming.priority,
            reason: incoming.reason,
            wall_ts: incoming.wall_ts,
            snapshot_url: incoming.snapshot_url,
            acknowledged: incoming.acknowledged,
            acknowledged_by_username: null,
            acknowledged_at: null,
          },
          ...prev,
        ];
      });
    }, [])
  );

  async function handleAddEntry(e: FormEvent) {
    e.preventDefault();
    if (!newPlate.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/watchlist", {
        method: "POST",
        body: JSON.stringify({ plate_text: newPlate.trim(), reason: newReason.trim(), priority: newPriority }),
      });
      setNewPlate("");
      setNewReason("");
      setNewPriority("medium");
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to add entry.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeactivate(id: string) {
    try {
      await apiFetch(`/watchlist/${id}`, { method: "DELETE" });
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to remove entry.");
    }
  }

  async function handleAcknowledge(id: string) {
    setAcknowledgingId(id);
    try {
      const updated = await apiFetch<WatchlistMatchOut>(`/watchlist/matches/${id}/acknowledge`, {
        method: "POST",
      });
      setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to acknowledge alert.");
    } finally {
      setAcknowledgingId(null);
    }
  }

  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Watchlist &amp; Alerts</h1>
        <p className="text-sm text-muted">
          Live feed of watchlist matches across your jurisdiction, correlated in real time.
        </p>
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[1fr_400px]">
        <Card className="flex min-h-0 flex-col">
          <CardHeader>
            <CardTitle>Watchlist entries</CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-4">
            {canWrite && (
              <form onSubmit={handleAddEntry} className="flex flex-wrap items-end gap-2">
                <div className="flex flex-col gap-1">
                  <label htmlFor="new-plate" className="text-xs font-medium text-muted">
                    Plate
                  </label>
                  <Input
                    id="new-plate"
                    value={newPlate}
                    onChange={(e) => setNewPlate(e.target.value)}
                    placeholder="GJ01AB1234"
                    className="w-40 uppercase"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="new-reason" className="text-xs font-medium text-muted">
                    Reason
                  </label>
                  <Input
                    id="new-reason"
                    value={newReason}
                    onChange={(e) => setNewReason(e.target.value)}
                    placeholder="Stolen vehicle report #..."
                    className="w-56"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="new-priority" className="text-xs font-medium text-muted">
                    Priority
                  </label>
                  <select
                    id="new-priority"
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as WatchlistPriority)}
                    className="h-9 rounded border border-border bg-surface px-2 text-sm"
                  >
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Adding…" : "Add to watchlist"}
                </Button>
              </form>
            )}

            <div className="min-h-0 flex-1 overflow-y-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeadCell>Plate</TableHeadCell>
                    <TableHeadCell>Priority</TableHeadCell>
                    <TableHeadCell>Reason</TableHeadCell>
                    <TableHeadCell>Added</TableHeadCell>
                    {canWrite && <TableHeadCell />}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {entries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-medium">{entry.plate_text}</TableCell>
                      <TableCell>
                        <Badge tone={entry.priority === "critical" || entry.priority === "high" ? "danger" : "neutral"}>
                          {entry.priority}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted">{entry.reason || "—"}</TableCell>
                      <TableCell className="text-muted">{new Date(entry.created_at).toLocaleDateString()}</TableCell>
                      {canWrite && (
                        <TableCell>
                          <Button variant="ghost" size="sm" onClick={() => void handleDeactivate(entry.id)}>
                            Remove
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {entries.length === 0 && <p className="p-4 text-sm text-muted">No active watchlist entries.</p>}
            </div>
          </CardContent>
        </Card>

        <Card className="flex min-h-0 flex-col">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Live alerts</CardTitle>
            {unacknowledgedCount > 0 && <Badge tone="danger">{unacknowledgedCount} unacknowledged</Badge>}
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            {alerts.length === 0 ? (
              <p className="text-sm text-muted">No alerts yet.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {alerts.map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    acknowledging={acknowledgingId === alert.id}
                    onAcknowledge={canAcknowledge ? (id) => void handleAcknowledge(id) : () => undefined}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
