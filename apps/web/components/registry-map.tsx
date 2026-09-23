"use client";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import MarkerClusterGroup from "react-leaflet-cluster";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import type { CameraOut } from "@/lib/types";

const GUJARAT_CENTER: [number, number] = [22.3, 71.8];

// camera.status isn't live-synced from go2rtc/stream_manager yet (see
// README.md "Known gaps") — colors reflect the registry's last-known
// value, not necessarily this second's real connection state. Every
// marker's popup also states the status in text, never color alone.
const STATUS_COLOR: Record<CameraOut["status"], string> = {
  live: "#059669", // success
  reconnecting: "#D97706", // warning
  offline: "#DC2626", // danger
  unknown: "#94A3B8", // muted slate
};

interface RegistryMapProps {
  cameras: CameraOut[];
  onSelect?: (camera: CameraOut) => void;
}

export default function RegistryMap({ cameras, onSelect }: RegistryMapProps) {
  const located = cameras.filter(
    (c): c is CameraOut & { lat: number; lon: number } => c.lat !== null && c.lon !== null
  );

  return (
    <MapContainer center={GUJARAT_CENTER} zoom={7} className="h-full w-full rounded">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MarkerClusterGroup chunkedLoading>
        {located.map((camera) => (
          <CircleMarker
            key={camera.id}
            center={[camera.lat, camera.lon]}
            radius={9}
            pathOptions={{
              color: STATUS_COLOR[camera.status],
              fillColor: STATUS_COLOR[camera.status],
              fillOpacity: 0.7,
              weight: 2,
            }}
            eventHandlers={{ click: () => onSelect?.(camera) }}
          >
            <Popup>
              <div className="text-xs">
                <div className="font-semibold">{camera.name}</div>
                <div>{camera.department}</div>
                <div>Status: {camera.status}</div>
                <div>Protocol: {camera.protocol || "unknown"}</div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MarkerClusterGroup>
    </MapContainer>
  );
}
