"""URL validation and platform detection.

This is the FIRST line of defense. Any URL that does not match the strict
allowlist of host patterns is rejected before it ever reaches yt-dlp.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.schemas import Platform

# Host -> Platform allowlist. Order matters: most specific first.
_HOST_MAP: list[Tuple[re.Pattern[str], Platform]] = [
    # YouTube
    (re.compile(r"^(www\.|m\.|music\.)?youtube\.com$", re.I), "youtube"),
    (re.compile(r"^youtu\.be$", re.I), "youtube"),
    # TikTok
    (re.compile(r"^(www\.|m\.|vm\.|vt\.)?tiktok\.com$", re.I), "tiktok"),
    # X / Twitter
    (re.compile(r"^(www\.|mobile\.)?(twitter|x)\.com$", re.I), "twitter"),
    # Facebook
    (re.compile(r"^(www\.|m\.|web\.)?facebook\.com$", re.I), "facebook"),
    (re.compile(r"^fb\.watch$", re.I), "facebook"),
]

_MAX_URL_LEN = 2048


class InvalidURLError(ValueError):
    """Raised when a URL fails validation."""


def detect_platform(url: str) -> Optional[Platform]:
    """Return the platform for a URL, or None if unsupported."""
    if not url or len(url) > _MAX_URL_LEN:
        return None
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    for pattern, platform in _HOST_MAP:
        if pattern.match(host):
            return platform
    return None


def validate_url(url: str) -> Tuple[str, Platform]:
    """Validate URL and return (cleaned_url, platform).

    Raises InvalidURLError if the URL is not from a supported platform.
    """
    if not isinstance(url, str):
        raise InvalidURLError("Invalid URL.")
    cleaned = url.strip()
    if not cleaned:
        raise InvalidURLError("URL cannot be empty.")
    if len(cleaned) > _MAX_URL_LEN:
        raise InvalidURLError("URL is too long.")
    # Reject control chars / whitespace inside (defense-in-depth vs injection)
    if any(c.isspace() or ord(c) < 32 for c in cleaned):
        raise InvalidURLError("URL contains invalid characters.")
    platform = detect_platform(cleaned)
    if platform is None:
        raise InvalidURLError(
            "Unsupported platform. ClipFetch supports YouTube, TikTok, X, and Facebook."
        )
    return cleaned, platform
