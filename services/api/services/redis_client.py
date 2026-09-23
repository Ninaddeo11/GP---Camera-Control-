"""Single shared Redis client, used for the refresh-token blacklist now and
the Phase 4+ event-stream consumers later."""

from __future__ import annotations

import redis.asyncio as redis

from config import settings

redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)
