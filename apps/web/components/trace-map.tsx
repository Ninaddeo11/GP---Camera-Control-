"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";

import type { CameraStop } from "@/lib/types";

// Leaflet's default marker icon assets are broken by bundlers unless
// re-pointed at CDN-hosted copies — using CircleMarker below sidesteps
// this entirely, so no icon config is needed for the route markers.
void L;

const GUJARAT_CENTER: [number, number] = [22.3, 71.8];

interface TraceMapProps {
  stops: CameraStop[];
}

export default function TraceMap({ stops }: TraceMapProps) {
  const located = stops.filter(
    (s): s is CameraStop & { lat: number; lon: number } => s.lat !== null && s.lon !== null
  );

  const firstStop = located[0];
  const center: [number, number] = firstStop ? [firstStop.lat, firstStop.lon] : GUJARAT_CENTER;
  const polylinePositions: [number, number][] = located.map((s) => [s.lat, s.lon]);

  return (
    <MapContainer center={center} zoom={located.length > 0 ? 11 : 7} className="h-full w-full rounded">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {polylinePositions.length >= 2 && (
        <Polyline positions={polylinePositions} pathOptions={{ color: "#1D4E9C", weight: 3 }} />
      )}
      {located.map((stop, index) => (
        <CircleMarker
          key={`${stop.camera_id}-${stop.first_seen}`}
          center={[stop.lat, stop.lon]}
          radius={8 + Math.min(stop.dwell_seconds / 60, 12)}
          pathOptions={{ color: "#1D4E9C", fillColor: "#1D4E9C", fillOpacity: 0.35, weight: 2 }}
        >
          <Popup>
            <div className="text-xs">
              <div className="font-semibold">
                #{index + 1} {stop.camera_name}
              </div>
              <div>{new Date(stop.first_seen).toLocaleString()}</div>
              <div>Dwell: {Math.round(stop.dwell_seconds)}s</div>
              {stop.inferred_speed_to_next_kmh !== null && (
                <div>Next leg: {stop.inferred_speed_to_next_kmh} km/h</div>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
