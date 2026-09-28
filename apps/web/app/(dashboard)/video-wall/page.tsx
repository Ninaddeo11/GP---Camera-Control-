"use client";

import { useEffect, useState } from "react";

import { useDialogFocus } from "@/lib/use-dialog-focus";
import { Input } from "@/components/ui/input";
import { cameraLocation, statusLabels } from "@/lib/camera-registry";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LiveFeed } from "@/components/live-feed";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import { useCameraFeed } from "@/lib/use-camera-feed";
import type { CameraOut } from "@/lib/types";

type GridSize = 2 | 3 | 4;

export default function VideoWallPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [cameras, setCameras] = useState<CameraOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gridSize, setGridSize] = useState<GridSize>(2);
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<CameraOut | null>(null);

  useEffect(() => {
    apiFetch<CameraOut[]>("/cameras")
      .then((data) => {
        setCameras(data);
        const cameraId = new URLSearchParams(window.location.search).get(
          "camera",
        );
        if (cameraId)
          setExpanded(data.find((c) => c.camera_id === cameraId) || null);
      })
      .catch((err) =>
        setError(
          err instanceof ApiRequestError
            ? err.message
            : "Failed to load cameras.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  // Each visible tile opens its own WebRTC/HLS connection and, server
  // side, its own transcode — rendering every camera at once (as this
  // page used to, regardless of grid size) tries to run dozens of those
  // simultaneously and none of them ever finish connecting, confirmed
  // against both a real 30-camera gateway and a resource-constrained
  // host. Paginating to exactly what the selected grid actually shows
  // keeps concurrent streams bounded to at most 16 (4×4).
  const filtered = cameras.filter(
    (c) =>
      [
        c.name,
        c.camera_id,
        c.department,
        cameraLocation(c, user?.jurisdictions || []),
      ].some((v) => v.toLowerCase().includes(search.toLowerCase())) &&
      (statusFilter === "all" || c.status === statusFilter),
  );
  const perPage = gridSize * gridSize;
  const pageCount = Math.max(1, Math.ceil(filtered.length / perPage));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleCameras = filtered.slice(
    currentPage * perPage,
    currentPage * perPage + perPage,
  );

  function changeGridSize(size: GridSize) {
    setGridSize(size);
    setPage(0);
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Video Wall</h1>
          <p className="text-sm text-muted">
            {cameras.length} camera{cameras.length === 1 ? "" : "s"} in your
            jurisdiction
          </p>
        </div>
        <div className="flex gap-1">
          {([2, 3, 4] as GridSize[]).map((size) => (
            <Button
              key={size}
              variant={gridSize === size ? "primary" : "secondary"}
              size="sm"
              onClick={() => changeGridSize(size)}
            >
              {size}×{size}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Input
          className="max-w-sm"
          aria-label="Search video cameras"
          placeholder="Search cameras?"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
        />
        <select
          aria-label="Camera status"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(0);
          }}
        >
          <option value="all">All statuses</option>
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {loading && (
        <p role="status" className="text-sm text-muted">
          Loading camera network?
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {filtered.length === 0 && !error && !loading ? (
        <p className="text-sm text-muted">No cameras match this view.</p>
      ) : (
        <div
          className="video-grid grid flex-1 gap-3 overflow-y-auto"
          style={{ gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))` }}
        >
          {visibleCameras.map((camera) => (
            <LiveFeed
              key={camera.id}
              camera={camera}
              onExpand={() => setExpanded(camera)}
            />
          ))}
        </div>
      )}

      {pageCount > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted">
            Page {currentPage + 1} of {pageCount}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={currentPage >= pageCount - 1}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </Button>
        </div>
      )}

      {expanded && (
        <ExpandedFeedModal
          camera={expanded}
          onClose={() => setExpanded(null)}
        />
      )}
    </div>
  );
}

function ExpandedFeedModal({
  camera,
  onClose,
}: {
  camera: CameraOut;
  onClose: () => void;
}) {
  const { videoRef, status } = useCameraFeed(camera.camera_id);
  const dialogRef = useDialogFocus(onClose);

  return (
    <div
      ref={dialogRef}
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
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="h-full w-full object-cover"
          />
        </div>
        <div className="w-64 shrink-0">
          <h2 className="text-base font-semibold text-foreground">
            {camera.name}
          </h2>
          <p className="text-sm text-muted">{camera.department}</p>
          <div className="mt-3 flex flex-col gap-2 text-sm">
            <Row label="Status">
              <Badge
                tone={
                  status === "live"
                    ? "success"
                    : status === "error"
                      ? "danger"
                      : "neutral"
                }
              >
                {status}
              </Badge>
            </Row>
            <Row label="Camera ID">{camera.camera_id}</Row>
            <Row label="Resolution">{camera.resolution || "unknown"}</Row>
            <Row label="Protocol">{camera.protocol || "unknown"}</Row>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="mt-4 w-full"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted">{label}</span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}
