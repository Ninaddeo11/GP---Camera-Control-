import type { CameraOut, JurisdictionOut } from "./types";

export const statusLabels = {
  live: "Online",
  reconnecting: "Warning",
  offline: "Offline",
  unknown: "Unknown",
} as const;
export const statusTones = {
  live: "accent",
  reconnecting: "warning",
  offline: "danger",
  unknown: "neutral",
} as const;
export function coordinates(
  lat: unknown,
  lon: unknown,
): [number, number] | null {
  const number = (value: unknown) =>
    typeof value === "number"
      ? value
      : typeof value === "string" && value.trim()
        ? Number(value)
        : NaN;
  const latitude = number(lat),
    longitude = number(lon);
  return Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    Math.abs(latitude) <= 90 &&
    Math.abs(longitude) <= 180
    ? [latitude, longitude]
    : null;
}
export function cameraLocation(
  camera: CameraOut,
  jurisdictions: JurisdictionOut[],
) {
  return (
    jurisdictions.find((j) => j.id === camera.jurisdiction_id)?.name ||
    (camera.jurisdiction_id
      ? "Assigned jurisdiction"
      : "Unassigned jurisdiction")
  );
}
export function registryDiagnostics(cameras: CameraOut[]) {
  const ids = new Set<string>(),
    cameraIds = new Set<string>(),
    locations = new Set<string>();
  let valid = 0,
    duplicateIds = 0,
    duplicateCoordinates = 0;
  cameras.forEach((camera) => {
    if (ids.has(camera.id) || cameraIds.has(camera.camera_id)) duplicateIds++;
    ids.add(camera.id);
    cameraIds.add(camera.camera_id);
    const position = coordinates(camera.lat, camera.lon);
    if (position) {
      valid++;
      const key = position.join(",");
      if (locations.has(key)) duplicateCoordinates++;
      locations.add(key);
    }
  });
  return {
    total: cameras.length,
    valid,
    unavailable: cameras.length - valid,
    duplicateIds,
    duplicateCoordinates,
    entities: valid,
  };
}

// Keys follow API record object identity through sorting/filtering; even malformed
// duplicate IDs remain visible without React reusing another camera's marker.
const recordKeys = new WeakMap<CameraOut, string>();
let recordSequence = 0;
export function cameraKey(camera: CameraOut) {
  let key = recordKeys.get(camera);
  if (!key) {
    key = `${camera.id}:${recordSequence++}`;
    recordKeys.set(camera, key);
  }
  return key;
}
