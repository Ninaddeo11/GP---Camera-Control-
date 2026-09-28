"use client";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, Popup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import { MapBaseLayer } from "@/components/map-base-layer";
import type { CameraOut } from "@/lib/types";
import { cameraKey, coordinates, statusLabels } from "@/lib/camera-registry";

interface Props {
  cameras: CameraOut[];
  selected: CameraOut | null;
  onSelect: (camera: CameraOut) => void;
  locationLabel: (camera: CameraOut) => string;
}
const cameraSvg =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 6-3v10l-6-3z"/></svg>';
function Layers({ cameras, selected, onSelect, locationLabel }: Props) {
  const map = useMap();
  const cluster = useRef<L.MarkerClusterGroup>(null);
  const markers = useRef(new Map<string, L.Marker>());
  const located = useMemo(
    () =>
      cameras.flatMap((camera) => {
        const position = coordinates(camera.lat, camera.lon);
        return position ? [{ camera, position }] : [];
      }),
    [cameras],
  );
  function fit() {
    if (located.length)
      map.fitBounds(L.latLngBounds(located.map((c) => c.position)), {
        padding: [45, 45],
        maxZoom: 16,
        animate: false,
      });
  }
  useEffect(() => {
    fit();
    if (process.env.NODE_ENV === "development")
      console.info("Map entity validation", {
        validCoordinates: located.length,
        renderedEntities: cluster.current?.getLayers().length || 0,
      });
  }, [located, map]); // Fit the filtered dataset, without recreating the map.
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  useEffect(() => {
    if (!selected) {
      map.closePopup();
      return;
    }
    const marker = markers.current.get(selected.id);
    if (!marker || !cluster.current?.hasLayer(marker)) return;
    // Use synchronous movement so filtering cannot leave the cluster plugin's
    // zoomToShowLayer callback pointing at a removed marker.
    const position = coordinates(selected.lat, selected.lon);
    if (!position) return;
    map.setView(position, map.getMaxZoom(), { animate: false });
    const parent = cluster.current.getVisibleParent(marker);
    if (parent instanceof L.MarkerCluster) parent.spiderfy();
    if (map.hasLayer(marker)) marker.openPopup();
  }, [selected, located]);
  return (
    <>
      <MarkerClusterGroup
        ref={cluster}
        animate={false}
        chunkedLoading
        maxClusterRadius={48}
        showCoverageOnHover={false}
        spiderfyOnMaxZoom
        iconCreateFunction={(group: L.MarkerCluster) =>
          L.divIcon({
            html: String(group.getChildCount()),
            className: "camera-cluster",
            iconSize: [42, 42],
          })
        }
      >
        {located.map(({ camera, position }) => (
          <Marker
            key={cameraKey(camera)}
            position={position}
            ref={(marker) => {
              if (marker) markers.current.set(camera.id, marker);
              else markers.current.delete(camera.id);
            }}
            title={`${camera.name} · ${statusLabels[camera.status]}`}
            alt={camera.name}
            icon={L.divIcon({
              html: cameraSvg,
              className: `camera-marker ${camera.status} ${selected?.id === camera.id ? "selected" : ""}`,
              iconSize: [32, 32],
              iconAnchor: [16, 16],
            })}
            eventHandlers={{ click: () => onSelect(camera) }}
          >
            <Popup>
              <div className="min-w-48 space-y-3 text-sm">
                <strong>{camera.name}</strong>
                <div>
                  {statusLabels[camera.status]}{" "}
                  <span className="text-muted">· Registry status</span>
                </div>
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  <dt>Camera ID</dt>
                  <dd>{camera.camera_id}</dd>
                  <dt>Location</dt>
                  <dd>{locationLabel(camera)}</dd>
                  <dt>Department</dt>
                  <dd>{camera.department || "Unavailable"}</dd>
                  <dt>Resolution</dt>
                  <dd>{camera.resolution || "Unavailable"}</dd>
                  <dt>Coordinates</dt>
                  <dd>{position.map((n) => n.toFixed(6)).join(", ")}</dd>
                </dl>
                <a
                  className="inline-block rounded bg-accent px-3 py-2 !text-white"
                  href={`/video-wall?camera=${encodeURIComponent(camera.camera_id)}`}
                >
                  View Camera
                </a>
              </div>
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>
      <div className="absolute right-3 top-3 z-[1000]">
        <button
          className="rounded border border-border bg-surface px-3 py-2 text-xs shadow"
          onClick={fit}
          disabled={!located.length}
        >
          Fit All Cameras
        </button>
      </div>
      <div
        className="absolute bottom-7 left-3 z-[1000] flex flex-wrap gap-3 rounded border border-border bg-surface/95 px-3 py-2 text-xs"
        aria-label="Map legend"
      >
        {Object.entries(statusLabels).map(([status, label]) => (
          <span key={status}>
            <span
              className={`inline-block mr-1 h-2 w-2 rounded-full ${status === "live" ? "bg-accent" : status === "offline" ? "bg-danger" : status === "reconnecting" ? "bg-warning" : "bg-muted"}`}
            />
            {label}
          </span>
        ))}
        <span>Cluster</span>
      </div>
      {!located.length && (
        <div className="absolute inset-0 z-[500] flex items-center justify-center bg-background/70 pointer-events-none">
          <p className="rounded bg-surface p-4 text-sm">
            No camera locations available for this view.
          </p>
        </div>
      )}
    </>
  );
}
export default function RegistryMap(props: Props) {
  // World bounds are only the empty-map viewport, never a camera location.
  return (
    <MapContainer
      bounds={[
        [-60, -170],
        [75, 170],
      ]}
      maxZoom={19}
      className="h-full min-h-[430px] w-full"
    >
      <MapBaseLayer />
      <Layers {...props} />
    </MapContainer>
  );
}
