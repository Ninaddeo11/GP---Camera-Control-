"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiFetch, ApiRequestError } from "@/lib/api-client";
import type { CameraOut } from "@/lib/types";

const RegistryMap = dynamic(() => import("@/components/registry-map"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-muted">Loading map…</div>,
});

export default function RegistryMapPage() {
  const [cameras, setCameras] = useState<CameraOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [departmentFilter, setDepartmentFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selected, setSelected] = useState<CameraOut | null>(null);

  useEffect(() => {
    apiFetch<CameraOut[]>("/cameras")
      .then(setCameras)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Failed to load cameras."));
  }, []);

  const departments = useMemo(
    () => Array.from(new Set(cameras.map((c) => c.department).filter(Boolean))).sort(),
    [cameras]
  );

  const filtered = cameras.filter(
    (c) =>
      (departmentFilter === "all" || c.department === departmentFilter) &&
      (statusFilter === "all" || c.status === statusFilter)
  );

  return (
    <div className="flex h-full gap-4">
      <Card className="flex w-64 shrink-0 flex-col overflow-y-auto">
        <CardContent className="flex flex-col gap-5">
          <div>
            <h1 className="text-base font-semibold text-foreground">Camera Registry</h1>
            <p className="mt-1 text-xs text-muted">{filtered.length} of {cameras.length} cameras shown</p>
          </div>

          <FilterGroup label="Department" value={departmentFilter} onChange={setDepartmentFilter} options={departments} />
          <FilterGroup
            label="Status"
            value={statusFilter}
            onChange={setStatusFilter}
            options={["live", "reconnecting", "offline", "unknown"]}
          />

          {error && (
            <p role="alert" className="text-xs text-danger">
              {error}
            </p>
          )}

          {selected && (
            <div className="rounded border border-border p-3">
              <div className="text-sm font-semibold text-foreground">{selected.name}</div>
              <div className="text-xs text-muted">{selected.department}</div>
              <div className="mt-2 flex flex-col gap-1 text-xs">
                <div>
                  Status: <Badge tone={selected.status === "live" ? "success" : selected.status === "offline" ? "danger" : "neutral"}>{selected.status}</Badge>
                </div>
                <div>Camera ID: {selected.camera_id}</div>
                <div>Resolution: {selected.resolution || "unknown"}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="min-h-0 flex-1 overflow-hidden">
        <RegistryMap cameras={filtered} onSelect={setSelected} />
      </Card>
    </div>
  );
}

function FilterGroup({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-medium text-muted">{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded border border-border bg-surface px-2 text-sm"
      >
        <option value="all">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}
