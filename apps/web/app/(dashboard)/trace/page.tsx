"use client";

import dynamic from "next/dynamic";
import { useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import type { TraversalResult } from "@/lib/types";

const TraceMap = dynamic(() => import("@/components/trace-map"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-muted">Loading map…</div>,
});

export default function VehicleTracePage() {
  const [plateInput, setPlateInput] = useState("");
  const [result, setResult] = useState<TraversalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    const plate = plateInput.trim();
    if (!plate) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<TraversalResult>(`/tracking/plate/${encodeURIComponent(plate)}`);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Something went wrong while searching for this plate."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    if (!result) return;
    setExporting(true);
    try {
      const exportResult = await apiFetch<{ download_url: string }>("/evidence/export", {
        method: "POST",
        body: JSON.stringify({ plate_text: result.plate_text }),
      });
      window.open(exportResult.download_url, "_blank");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Vehicle Trace</h1>
        <p className="text-sm text-muted">
          Search a plate to reconstruct its route across every camera in your jurisdiction.
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex max-w-md gap-2">
        <Input
          value={plateInput}
          onChange={(e) => setPlateInput(e.target.value)}
          placeholder="e.g. GJ01AB1234"
          aria-label="Plate number"
          className="uppercase"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </form>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {result && (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
          <Card className="flex min-h-0 flex-col">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>
                {result.plate_text} — {result.stops.length} stop{result.stops.length === 1 ? "" : "s"}
              </CardTitle>
              <Button variant="secondary" size="sm" onClick={handleExport} disabled={exporting || result.stops.length === 0}>
                {exporting ? "Exporting…" : "Export evidence"}
              </Button>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              {result.omitted_out_of_jurisdiction_stops > 0 && (
                <p className="mb-3 text-xs text-muted">
                  {result.omitted_out_of_jurisdiction_stops} additional detection
                  {result.omitted_out_of_jurisdiction_stops === 1 ? "" : "s"} exist outside your
                  jurisdiction and are not shown.
                </p>
              )}
              {result.stops.length === 0 ? (
                <p className="text-sm text-muted">No detections found for this plate in your jurisdiction.</p>
              ) : (
                <ol className="flex flex-col gap-3">
                  {result.stops.map((stop, index) => (
                    <li key={`${stop.camera_id}-${stop.first_seen}`} className="rounded border border-border p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-foreground">
                          #{index + 1} {stop.camera_name}
                        </span>
                        <Badge tone="accent">{Math.round(stop.confidence_avg * 100)}% conf</Badge>
                      </div>
                      <div className="mt-1 text-xs text-muted">
                        {new Date(stop.first_seen).toLocaleString()}
                        {stop.dwell_seconds > 1 && <> · dwell {Math.round(stop.dwell_seconds)}s</>}
                      </div>
                      {stop.inferred_speed_to_next_kmh !== null && (
                        <div className="mt-1 text-xs text-muted">
                          → next stop: {stop.inferred_speed_to_next_kmh} km/h
                        </div>
                      )}
                      {stop.snapshot_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={stop.snapshot_url}
                          alt={`Snapshot from ${stop.camera_name}`}
                          className="mt-2 h-20 w-full rounded object-cover"
                        />
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>

          <Card className="min-h-[400px] overflow-hidden">
            <TraceMap stops={result.stops} />
          </Card>
        </div>
      )}
    </div>
  );
}
