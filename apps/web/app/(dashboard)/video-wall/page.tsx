"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LiveFeed } from "@/components/live-feed";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import { useWhep } from "@/lib/use-whep";
import type { CameraOut } from "@/lib/types";

type GridSize = 2 | 3 | 4;

export default function VideoWallPage() {
  const [cameras, setCameras] = useState<CameraOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gridSize, setGridSize] = useState<GridSize>(2);
  const [expanded, setExpanded] = useState<CameraOut | null>(null);

  useEffect(() => {
    apiFetch<CameraOut[]>("/cameras")
      .then(setCameras)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Failed to load cameras."));
  }, []);

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Video Wall</h1>
          <p className="text-sm text-muted">{cameras.length} camera{cameras.length === 1 ? "" : "s"} in your jurisdiction</p>
        </div>
        <div className="flex gap-1">
          {([2, 3, 4] as GridSize[]).map((size) => (
            <Button
              key={size}
              variant={gridSize === size ? "primary" : "secondary"}
              size="sm"
              onClick={() => setGridSize(size)}
            >
              {size}×{size}
            </Button>
          ))}
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {cameras.length === 0 && !error ? (
        <p className="text-sm text-muted">No cameras are visible in your jurisdiction yet.</p>
      ) : (
        <div
          className="grid flex-1 gap-3 overflow-y-auto"
          style={{ gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))` }}
        >
          {cameras.map((camera) => (
            <LiveFeed key={camera.id} camera={camera} onExpand={() => setExpanded(camera)} />
          ))}
        </div>
      )}

      {expanded && <ExpandedFeedModal camera={expanded} onClose={() => setExpanded(null)} />}
    </div>
  );
}

function ExpandedFeedModal({ camera, onClose }: { camera: CameraOut; onClose: () => void }) {
  const { videoRef, status } = useWhep(camera.camera_id);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Expanded view of ${camera.name}`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
      onClick={onClose}
    >
      <div
        className="flex w-full max-w-5xl gap-4 rounded bg-surface p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="aspect-video flex-1 overflow-hidden rounded bg-surface-muted">
          <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
        </div>
        <div className="w-64 shrink-0">
          <h2 className="text-base font-semibold text-foreground">{camera.name}</h2>
          <p className="text-sm text-muted">{camera.department}</p>
          <div className="mt-3 flex flex-col gap-2 text-sm">
            <Row label="Status">
              <Badge tone={status === "live" ? "success" : status === "error" ? "danger" : "neutral"}>
                {status}
              </Badge>
            </Row>
            <Row label="Camera ID">{camera.camera_id}</Row>
            <Row label="Resolution">{camera.resolution || "unknown"}</Row>
            <Row label="Protocol">{camera.protocol || "unknown"}</Row>
          </div>
          <Button variant="secondary" size="sm" className="mt-4 w-full" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted">{label}</span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}
