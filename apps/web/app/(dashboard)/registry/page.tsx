"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  cameraKey,
  cameraLocation,
  coordinates,
  registryDiagnostics,
  statusLabels,
  statusTones,
} from "@/lib/camera-registry";
import type { CameraOut } from "@/lib/types";
const RegistryMap = dynamic(() => import("@/components/registry-map"), {
  ssr: false,
  loading: () => (
    <div role="status" className="grid h-full place-items-center text-muted">
      Loading map…
    </div>
  ),
});
export default function RegistryMapPage() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<CameraOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("all");
  const [status, setStatus] = useState("all");
  const [location, setLocation] = useState("all");
  const [sort, setSort] = useState("name");
  const [selected, setSelected] = useState<CameraOut | null>(null);
  const cards = useRef(new Map<string, HTMLButtonElement>());
  const locationLabel = useCallback(
    (camera: CameraOut) => cameraLocation(camera, user?.jurisdictions || []),
    [user],
  );
  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch<CameraOut[]>("/cameras")
      .then(setCameras)
      .catch((err) =>
        setError(
          err instanceof ApiRequestError
            ? err.message
            : "Unable to load camera registry.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    load();
    setSearch(new URLSearchParams(window.location.search).get("q") || "");
  }, [load]);
  const diagnostics = useMemo(() => registryDiagnostics(cameras), [cameras]);
  useEffect(() => {
    if (!loading && !error && process.env.NODE_ENV === "development")
      console.info("Camera registry validation", diagnostics);
  }, [diagnostics, loading, error]);
  const departments = useMemo(
    () => [...new Set(cameras.map((c) => c.department).filter(Boolean))].sort(),
    [cameras],
  );
  const locations = useMemo(
    () =>
      [...new Set(cameras.map((c) => c.jurisdiction_id || "unassigned"))].map(
        (id) => ({
          value: id,
          label: locationLabel(
            cameras.find((c) => (c.jurisdiction_id || "unassigned") === id)!,
          ),
        }),
      ),
    [cameras, locationLabel],
  );
  const filtered = useMemo(
    () =>
      cameras
        .filter(
          (c) =>
            (department === "all" || c.department === department) &&
            (status === "all" || c.status === status) &&
            (location === "all" ||
              (location === "unavailable"
                ? !coordinates(c.lat, c.lon)
                : (c.jurisdiction_id || "unassigned") === location)) &&
            [c.name, c.camera_id, c.department, locationLabel(c)].some((v) =>
              v.toLowerCase().includes(search.trim().toLowerCase()),
            ),
        )
        .sort((a, b) => {
          const value = (c: CameraOut) =>
            sort === "location"
              ? locationLabel(c)
              : sort === "id"
                ? c.camera_id
                : sort === "status"
                  ? statusLabels[c.status]
                  : c.name;
          return value(a).localeCompare(value(b), undefined, { numeric: true });
        }),
    [cameras, department, status, location, search, sort, locationLabel],
  );
  const visibleDiagnostics = useMemo(
    () => registryDiagnostics(filtered),
    [filtered],
  );
  useEffect(() => {
    if (search.trim() && filtered.length === 1)
      setSelected(filtered[0] ?? null);
    else
      setSelected((current) =>
        current && filtered.some((c) => c.id === current.id) ? current : null,
      );
  }, [filtered, search]);
  useEffect(() => {
    if (selected)
      cards.current
        .get(selected.id)
        ?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [selected]);
  function reset() {
    setSearch("");
    setDepartment("all");
    setStatus("all");
    setLocation("all");
  }
  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium tracking-widest text-muted">
            CAMERA NETWORK
          </p>
          <h1 className="font-semibold">Registry Map</h1>
          <p className="text-sm text-muted">
            Geographic coverage and camera inventory
          </p>
        </div>
        <span className="text-xs text-muted">
          Statuses reflect the last registry update
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 lg:grid-cols-6">
        {[
          {
            label: "Total cameras",
            count: filtered.length,
            tone: "text-foreground",
          },
          ...Object.entries(statusLabels).map(([key, label]) => ({
            label,
            count: filtered.filter((c) => c.status === key).length,
            tone:
              key === "offline"
                ? "text-danger"
                : key === "reconnecting"
                  ? "text-warning"
                  : key === "live"
                    ? "text-[rgb(var(--cyan))]"
                    : "text-muted",
          })),
        ].map((item) => (
          <Card key={item.label} className="px-4 py-3">
            <div className={`text-2xl font-semibold tabular-nums ${item.tone}`}>
              {loading || error ? "—" : item.count}
            </div>
            <div className="text-xs text-muted">{item.label}</div>
          </Card>
        ))}
        <Card className="px-4 py-3">
          <div className="text-2xl font-semibold tabular-nums">
            {loading || error ? "—" : visibleDiagnostics.valid}
          </div>
          <div className="text-xs text-muted">Valid locations</div>
        </Card>
      </div>
      {error && (
        <div
          role="alert"
          className="flex items-center justify-between rounded border border-danger/40 bg-danger/10 p-3 text-sm"
        >
          <span>Unable to load camera registry. {error}</span>
          <Button size="sm" onClick={load}>
            Retry
          </Button>
        </div>
      )}
      {diagnostics.duplicateIds > 0 && (
        <p role="alert" className="text-sm text-warning">
          Registry data contains {diagnostics.duplicateIds} duplicate IDs.
          Records remain visible; identity-based selection may be ambiguous.
        </p>
      )}
      {selected && (
        <aside
          aria-label="Selected camera details"
          className="fixed inset-x-2 bottom-2 z-[1100] max-h-[38dvh] overflow-y-auto rounded-xl border border-accent/50 bg-surface p-4 shadow-xl md:hidden"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">{selected.name}</h2>
              <p className="mt-1 text-xs text-muted">
                {selected.camera_id} ? {locationLabel(selected)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              aria-label="Close camera details"
              onClick={() => setSelected(null)}
            >
              Close
            </Button>
          </div>
          <div className="my-3 flex flex-wrap items-center gap-3 text-xs">
            <Badge tone={statusTones[selected.status]}>
              {statusLabels[selected.status]}
            </Badge>
            <span>{selected.department || "Department unavailable"}</span>
            <span>{selected.resolution || "Resolution unavailable"}</span>
          </div>
          <p className="mb-3 text-xs text-muted">
            {coordinates(selected.lat, selected.lon)
              ?.map((value) => value.toFixed(6))
              .join(", ") || "Location unavailable"}
          </p>
          <a
            className="text-sm text-[rgb(var(--cyan))]"
            href={`/video-wall?camera=${encodeURIComponent(selected.camera_id)}`}
          >
            View Camera
          </a>
        </aside>
      )}
      <div className="registry-layout gap-4">
        <Card className="registry-list-panel flex min-h-0 flex-col overflow-hidden">
          <div className="space-y-3 border-b border-border p-4">
            <div className="flex justify-between">
              <h2 className="text-sm font-semibold">Camera registry</h2>
              <span className="text-xs text-muted">
                {filtered.length} / {cameras.length}
              </span>
            </div>
            <Input
              aria-label="Search cameras"
              placeholder="Search name, ID, location…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-2">
              <Filter
                label="Department"
                value={department}
                onChange={setDepartment}
                options={departments.map((d) => ({ value: d, label: d }))}
              />
              <Filter
                label="Status"
                value={status}
                onChange={setStatus}
                options={Object.entries(statusLabels).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
              <Filter
                label="Location"
                value={location}
                onChange={setLocation}
                options={[
                  ...locations,
                  { value: "unavailable", label: "Location unavailable" },
                ]}
              />
              <Filter
                label="Sort by"
                value={sort}
                onChange={setSort}
                options={["name", "id", "status", "location"].map((value) => ({
                  value,
                  label:
                    value === "id"
                      ? "ID"
                      : value.charAt(0).toUpperCase() + value.slice(1),
                }))}
                noAll
              />
            </div>
            <button className="text-xs text-[rgb(var(--cyan))]" onClick={reset}>
              Clear filters
            </button>
          </div>
          <div
            className="min-h-0 flex-1 overflow-y-auto p-2"
            aria-label="Camera results"
            aria-busy={loading}
          >
            {loading ? (
              <p role="status" className="p-4 text-sm text-muted">
                Loading camera registry…
              </p>
            ) : (
              filtered.map((camera) => (
                <button
                  key={cameraKey(camera)}
                  ref={(el) => {
                    if (el) cards.current.set(camera.id, el);
                    else cards.current.delete(camera.id);
                  }}
                  onClick={() => setSelected(camera)}
                  aria-pressed={selected?.id === camera.id}
                  className={`mb-2 w-full rounded border p-3 text-left ${selected?.id === camera.id ? "border-accent bg-accent/15" : "border-transparent bg-surface-muted/40 hover:border-border"}`}
                >
                  <div className="truncate text-sm font-semibold">
                    {camera.name}
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <span className="truncate font-mono text-xs text-muted">
                      {camera.camera_id}
                    </span>
                    <Badge tone={statusTones[camera.status]}>
                      {statusLabels[camera.status]}
                    </Badge>
                  </div>
                  <div className="mt-2 truncate text-xs text-muted">
                    {locationLabel(camera)} ·{" "}
                    {camera.department || "No department"}
                  </div>
                  {!coordinates(camera.lat, camera.lon) && (
                    <p className="mt-1 text-xs text-warning">
                      Location unavailable
                    </p>
                  )}
                </button>
              ))
            )}
            {!loading && !error && !filtered.length && (
              <p role="status" className="p-4 text-sm text-muted">
                {cameras.length
                  ? "No cameras match your filters."
                  : "No cameras found."}
              </p>
            )}
          </div>
          {selected && !coordinates(selected.lat, selected.lon) && (
            <div className="border-t border-border p-3 text-xs">
              <strong>{selected.name}</strong>
              <p className="my-2 text-warning">Camera location unavailable.</p>
              <a
                className="text-[rgb(var(--cyan))]"
                href={`/video-wall?camera=${encodeURIComponent(selected.camera_id)}`}
              >
                View Camera ?
              </a>
            </div>
          )}
        </Card>
        <Card className="registry-map-panel relative flex min-h-0 flex-col overflow-hidden">
          <div className="flex flex-wrap justify-between gap-2 border-b border-border px-4 py-3 text-xs">
            <span className="font-medium">Location coverage</span>
            <span role="status" className="text-muted">
              {loading
                ? "Loading…"
                : error
                  ? "Registry unavailable"
                  : `${visibleDiagnostics.valid} camera entities represented · ${visibleDiagnostics.unavailable} locations unavailable`}
            </span>
          </div>
          <div className="relative min-h-0 flex-1">
            <RegistryMap
              cameras={filtered}
              selected={selected}
              onSelect={setSelected}
              locationLabel={locationLabel}
            />
          </div>
        </Card>
      </div>
    </div>
  );
}
function Filter({
  label,
  value,
  onChange,
  options,
  noAll = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  noAll?: boolean;
}) {
  return (
    <label className="block min-w-0 text-xs text-muted">
      {label}
      <select
        aria-label={label}
        className="mt-1 w-full text-xs text-foreground"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {!noAll && <option value="all">All</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
