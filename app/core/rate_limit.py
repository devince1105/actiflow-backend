# app/core/rate_limit.py

import time
from collections import defaultdict
from functools import wraps
from fastapi import HTTPException, Request, status
from typing import Dict, Tuple

# In-memory storage for rate limiting (per-IP for anonymous registration protection)
# In production, this should be Redis
_rate_limit_db: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

def rate_limit_per_ip(limit: int, window: int, key_prefix: str = "reg"):
    """
    Adjusted Rate Limit: IP-based per specific resource (key_prefix + event_uuid)
    to avoid blocking an entire school/office on other events.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            event_uuid = kwargs.get("event_uuid")  # Get from URL params

            if not request or not event_uuid:
                return await func(*args, **kwargs)

            ip = request.client.host if request.client else "unknown"
            # Granular key: reg:uuid:ip
            key = f"{key_prefix}:{event_uuid}:{ip}"
            now = time.time()
            count, last_time = _rate_limit_db[key]

            if now - last_time > window:
                # Reset window
                _rate_limit_db[key] = (1, now)
            else:
                if count >= limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many registration attempts. Please wait a moment."
                        }
                    )
                _rate_limit_db[key] = (count + 1, last_time)

            return await func(*args, **kwargs)
        return wrapper
    return decorator
