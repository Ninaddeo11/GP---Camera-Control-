"""Thin PostGIS helper — geodesic (not naive Euclidean-on-degrees)
distance between two lat/lon points, used by vehicle_trace.py to infer
travel speed between consecutive camera stops.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def distance_km(db: AsyncSession, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    result = await db.execute(
        text(
            "SELECT ST_Distance("
            "ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326)::geography, "
            "ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)::geography"
            ") / 1000.0"
        ),
        {"lon1": lon1, "lat1": lat1, "lon2": lon2, "lat2": lat2},
    )
    return float(result.scalar_one())
