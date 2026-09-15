# app/core/rate_limit.py

import time
from threading import Lock
from collections import defaultdict
from fastapi import HTTPException, Request, status
from typing import Dict, Tuple

# In-memory storage for rate limiting (per-IP for anonymous registration protection)
# In production, this should be Redis
_rate_limit_db: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
_rate_limit_lock = Lock()


def check_rate_limit_per_ip(
    request: Request,
    event_uuid: object,
    *,
    limit: int = 5,
    window: int = 60,
    key_prefix: str = "reg",
) -> None:
    """Consume one request from a per-process, per-event IP rate limit."""
    ip = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{event_uuid}:{ip}"
    now = time.monotonic()

    with _rate_limit_lock:
        count, window_started_at = _rate_limit_db[key]
        if now - window_started_at >= window:
            _rate_limit_db[key] = (1, now)
            return
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        "Too many registration attempts. "
                        "Please wait a moment."
                    ),
                },
            )
        _rate_limit_db[key] = (count + 1, window_started_at)
