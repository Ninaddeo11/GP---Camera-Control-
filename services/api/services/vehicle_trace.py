"""Reconstructs a vehicle's cross-camera route from persisted plate reads:
plate string -> ordered detection events -> camera stops with dwell time
and inferred inter-camera travel speed.

Fuzzy matching (rapidfuzz, per the project brief) exists because two
genuine reads of the same physical plate can still differ by a character
even after anpr.py's own normalization/correction — a coarse SQL prefix
filter bounds the candidate set, then rapidfuzz.ratio narrows it to real
near-matches rather than unrelated plates that happen to share a prefix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.shape import to_shape
from models.camera import Camera
from models.plate_event import PlateEventRecord
from models.rbac import User
from schemas.tracking import CameraStop, RouteFeature, RouteGeoJSON, TraversalResult
from services import geo, media
from services.jurisdiction_service import get_user_scope_jurisdiction_ids

FUZZY_MATCH_THRESHOLD = 90.0


async def find_matching_plate_texts(db: AsyncSession, plate_query: str) -> list[str]:
    """Distinct plate_text values in the DB that fuzzy-match plate_query —
    a search for "GJ01AB1234" also picks up "GJ01AB1235" if that's really
    the same plate misread once, but not an unrelated "GJ05CD6789".
    """
    prefix = plate_query[:4]
    candidates = (
        await db.execute(
            select(PlateEventRecord.plate_text)
            .where(PlateEventRecord.plate_text.startswith(prefix))
            .distinct()
        )
    ).scalars().all()

    return [
        c for c in candidates
        if fuzz.ratio(plate_query, c) >= FUZZY_MATCH_THRESHOLD
    ]


@dataclass
class _VisitAccumulator:
    camera_id: str
    first_seen: datetime
    last_seen: datetime
    confidences: list[float] = field(default_factory=list)
    best_snapshot_path: str = ""
    best_confidence: float = 0.0

    def add(self, event: PlateEventRecord) -> None:
        self.last_seen = event.wall_ts
        self.confidences.append(event.confidence)
        if event.confidence > self.best_confidence:
            self.best_confidence = event.confidence
            self.best_snapshot_path = event.snapshot_path


def _group_into_visits(events: list[PlateEventRecord]) -> list[_VisitAccumulator]:
    """Consecutive (in time) events at the same camera collapse into one
    stop with a dwell time; a later re-visit to that same camera becomes a
    separate stop, which is what a route/timeline actually means.
    """
    visits: list[_VisitAccumulator] = []
    for event in events:
        if visits and visits[-1].camera_id == event.camera_id:
            visits[-1].add(event)
        else:
            visit = _VisitAccumulator(
                camera_id=event.camera_id, first_seen=event.wall_ts, last_seen=event.wall_ts
            )
            visit.add(event)
            visits.append(visit)
    return visits


async def build_traversal(db: AsyncSession, plate_query: str, user: User) -> TraversalResult:
    plate_texts = await find_matching_plate_texts(db, plate_query)
    if not plate_texts:
        return TraversalResult(plate_text=plate_query, stops=[], omitted_out_of_jurisdiction_stops=0)

    events = (
        await db.execute(
            select(PlateEventRecord)
            .where(PlateEventRecord.plate_text.in_(plate_texts))
            .order_by(PlateEventRecord.wall_ts.asc())
        )
    ).scalars().all()

    scope_ids = await get_user_scope_jurisdiction_ids(db, user)
    camera_ids = {e.camera_id for e in events}
    cameras = (
        await db.execute(select(Camera).where(Camera.camera_id.in_(camera_ids)))
    ).scalars().all()
    cameras_by_id = {c.camera_id: c for c in cameras}

    # A camera the registry doesn't know about, or that isn't in the
    # caller's jurisdiction, is dropped from the route entirely rather
    # than shown with placeholder data — a partial route with a gap is
    # honest; a route through an unauthorized camera is a jurisdiction
    # leak, and a route through an unregistered camera is unverifiable.
    visible_events = []
    omitted = 0
    for event in events:
        camera = cameras_by_id.get(event.camera_id)
        if camera is None or camera.jurisdiction_id not in scope_ids:
            omitted += 1
            continue
        visible_events.append(event)

    visits = _group_into_visits(visible_events)

    stops: list[CameraStop] = []
    for i, visit in enumerate(visits):
        camera = cameras_by_id[visit.camera_id]
        lat = lon = None
        if camera.location is not None:
            point = to_shape(camera.location)
            lon, lat = point.x, point.y

        speed_kmh = None
        if i + 1 < len(visits):
            next_camera = cameras_by_id[visits[i + 1].camera_id]
            if camera.location is not None and next_camera.location is not None:
                p1, p2 = to_shape(camera.location), to_shape(next_camera.location)
                distance_km = await geo.distance_km(db, p1.y, p1.x, p2.y, p2.x)
                gap_hours = (visits[i + 1].first_seen - visit.last_seen).total_seconds() / 3600.0
                if gap_hours > 0:
                    speed_kmh = round(distance_km / gap_hours, 1)

        stops.append(
            CameraStop(
                camera_id=camera.camera_id,
                camera_name=camera.name,
                lat=lat,
                lon=lon,
                first_seen=visit.first_seen,
                last_seen=visit.last_seen,
                dwell_seconds=(visit.last_seen - visit.first_seen).total_seconds(),
                confidence_avg=sum(visit.confidences) / len(visit.confidences),
                snapshot_url=media.snapshot_url(visit.best_snapshot_path),
                inferred_speed_to_next_kmh=speed_kmh,
            )
        )

    return TraversalResult(
        plate_text=plate_query, stops=stops, omitted_out_of_jurisdiction_stops=omitted
    )


def to_route_geojson(traversal: TraversalResult) -> RouteGeoJSON:
    located_stops = [s for s in traversal.stops if s.lat is not None and s.lon is not None]

    features = [
        RouteFeature(
            geometry={"type": "Point", "coordinates": [s.lon, s.lat]},
            properties={
                "camera_id": s.camera_id,
                "camera_name": s.camera_name,
                "first_seen": s.first_seen.isoformat(),
                "last_seen": s.last_seen.isoformat(),
                "dwell_seconds": s.dwell_seconds,
                "sequence": i,
            },
        )
        for i, s in enumerate(located_stops)
    ]

    if len(located_stops) >= 2:
        features.append(
            RouteFeature(
                geometry={
                    "type": "LineString",
                    "coordinates": [[s.lon, s.lat] for s in located_stops],
                },
                properties={"kind": "route"},
            )
        )

    return RouteGeoJSON(features=features)
