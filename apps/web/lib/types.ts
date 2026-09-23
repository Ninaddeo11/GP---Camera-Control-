// Hand-maintained to mirror services/api's Pydantic schemas. The plan
// (README.md "Repository layout") is to generate this file from the
// backend's OpenAPI schema (e.g. via openapi-typescript) once the schema
// stabilizes — until then, keep this in sync by hand when a backend
// schema changes.

export interface JurisdictionOut {
  id: string;
  code: string;
  name: string;
  scope_type: string;
}

export interface MeResponse {
  id: string;
  username: string;
  full_name: string;
  badge_number: string | null;
  department: string | null;
  role_code: string;
  role_name: string;
  permissions: string[];
  jurisdictions: JurisdictionOut[];
}

export interface CameraOut {
  id: string;
  camera_id: string;
  name: string;
  department: string;
  jurisdiction_id: string | null;
  lat: number | null;
  lon: number | null;
  protocol: string;
  resolution: string;
  codec: string;
  fps: number;
  status: "unknown" | "live" | "offline" | "reconnecting";
  is_active: boolean;
  updated_at: string;
}

export interface CameraStop {
  camera_id: string;
  camera_name: string;
  lat: number | null;
  lon: number | null;
  first_seen: string;
  last_seen: string;
  dwell_seconds: number;
  confidence_avg: number;
  snapshot_url: string | null;
  inferred_speed_to_next_kmh: number | null;
}

export interface TraversalResult {
  plate_text: string;
  stops: CameraStop[];
  omitted_out_of_jurisdiction_stops: number;
}

export interface RouteGeoJSON {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: string; coordinates: unknown };
    properties: Record<string, unknown>;
  }>;
}

export interface RecentDetectionOut {
  id: string;
  camera_id: string;
  camera_name: string;
  plate_text: string;
  confidence: number;
  vehicle_class: string;
  wall_ts: string;
  snapshot_url: string | null;
}

export type WatchlistPriority = "low" | "medium" | "high" | "critical";

export interface WatchlistEntryOut {
  id: string;
  plate_text: string;
  reason: string;
  priority: WatchlistPriority;
  active: boolean;
  created_at: string;
}

export interface WatchlistMatchOut {
  id: string;
  watchlist_id: string;
  watchlist_plate_text: string;
  camera_id: string;
  camera_name: string;
  matched_plate_text: string;
  match_score: number;
  confidence: number;
  priority: WatchlistPriority;
  reason: string;
  wall_ts: string;
  snapshot_url: string | null;
  acknowledged: boolean;
  acknowledged_by_username: string | null;
  acknowledged_at: string | null;
}

export interface WatchlistAlertMessage {
  type: "watchlist_match";
  match_id: string;
  watchlist_id: string;
  watchlist_plate_text: string;
  matched_plate_text: string;
  match_score: number;
  priority: WatchlistPriority;
  reason: string;
  camera_id: string;
  camera_name: string;
  confidence: number;
  wall_ts: string;
  snapshot_url: string | null;
  acknowledged: boolean;
}

export interface ApiError {
  detail: string;
  code: string;
}
