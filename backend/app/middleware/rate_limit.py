"""IP-based rate limiting via SlowAPI.

Honors X-Forwarded-For when TRUST_PROXY=true (set this only behind a
trusted reverse proxy like Nginx/Cloudflare).
"""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")
FETCH_RATE = os.getenv("RATE_LIMIT_FETCH", "10/minute")
DOWNLOAD_RATE = os.getenv("RATE_LIMIT_DOWNLOAD", "30/minute")


def _client_id(request: Request) -> str:
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            # First entry is the original client IP
            return fwd.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_id, default_limits=[])

__all__ = ["limiter", "FETCH_RATE", "DOWNLOAD_RATE"]
