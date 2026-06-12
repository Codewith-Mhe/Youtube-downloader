"""YouTube-specific error classification.

Converts raw yt-dlp exceptions into user-friendly ExtractionError instances
with appropriate HTTP status codes.  Kept separate so the classifier can be
updated without touching extractor logic.
"""
from __future__ import annotations

import logging

from yt_dlp.utils import GeoRestrictedError, UnsupportedError

log = logging.getLogger("clipfetch.youtube.errors")


class YoutubeExtractionError(Exception):
    """User-facing YouTube extraction failure."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def classify_youtube_error(err: BaseException) -> YoutubeExtractionError:
    """Map an exception from yt-dlp to a YoutubeExtractionError.

    Rules are ordered from most-specific to least-specific so the first
    matching condition wins.
    """
    msg = str(err).lower()

    # ── ffmpeg / post-processor ───────────────────────────────────────────
    if "ffmpeg" in msg and any(
        kw in msg for kw in ("not found", "not installed", "is required", "no such file")
    ):
        return YoutubeExtractionError(
            "The server is missing ffmpeg, which is required to merge video and "
            "audio streams.  The operator needs to install ffmpeg.",
            status=500,
        )

    # ── bot / sign-in / cookie verification ──────────────────────────────
    if any(
        phrase in msg
        for phrase in (
            "sign in to confirm",
            "not a bot",
            "confirm you're not",
            "confirm you are not",
            "complete a captcha",
            "please sign in",
            "bot detection",
        )
    ):
        return YoutubeExtractionError(
        "YouTube downloads are temporarily unavailable on our server. ",
        status=429,
    )

    # ── expired / invalid cookies ─────────────────────────────────────────
    if "cookies" in msg and any(
        kw in msg for kw in ("expired", "invalid", "corrupt", "malformed")
    ):
        return YoutubeExtractionError(
            "The YouTube cookies file is expired or invalid.  "
            "Please export fresh cookies and update YT_COOKIES_FILE.",
            status=401,
        )

    # ── age-restricted ────────────────────────────────────────────────────
    if "age" in msg and any(kw in msg for kw in ("restrict", "sign in", "confirm", "gate")):
        return YoutubeExtractionError(
            "This video is age-restricted.  "
            "Provide valid YouTube cookies via YT_COOKIES_FILE to download it.",
            status=403,
        )

    # ── private / members-only ────────────────────────────────────────────
    if "private" in msg:
        return YoutubeExtractionError("This video is private.", status=403)
    if "members" in msg and "only" in msg:
        return YoutubeExtractionError(
            "This video is for channel members only.", status=403
        )

    # ── login required (generic) ──────────────────────────────────────────
    if "login" in msg or (
        "sign in" in msg and "confirm" not in msg and "bot" not in msg
    ):
        return YoutubeExtractionError(
            "Sign-in is required for this video.  "
            "Provide YouTube cookies via YT_COOKIES_FILE.",
            status=403,
        )

    # ── removed / deleted / unavailable ──────────────────────────────────
    if any(kw in msg for kw in ("removed", "deleted", "no longer available")):
        return YoutubeExtractionError("This video has been removed.", status=404)
    if any(
        kw in msg
        for kw in ("not available", "unavailable", "does not exist", "video unavailable")
    ):
        return YoutubeExtractionError("This video is unavailable.", status=404)

    # ── geo-restriction ───────────────────────────────────────────────────
    if isinstance(err, GeoRestrictedError) or (
        "geo" in msg and "restrict" in msg
    ):
        return YoutubeExtractionError(
            "This video is geo-restricted and cannot be accessed from this server.",
            status=451,
        )

    # ── unsupported URL ───────────────────────────────────────────────────
    if isinstance(err, UnsupportedError):
        return YoutubeExtractionError(
            "This YouTube URL is not supported.", status=400
        )

    # ── rate-limiting ─────────────────────────────────────────────────────
    if "http error 429" in msg or "too many requests" in msg or "ratelimit" in msg:
        return YoutubeExtractionError(
            "YouTube is rate-limiting requests from this server.  "
            "Please try again in a few minutes.",
            status=429,
        )

    # ── timeout ───────────────────────────────────────────────────────────
    if "timed out" in msg or "timeout" in msg or "read timed out" in msg:
        return YoutubeExtractionError(
            "The request to YouTube timed out.  Please try again.",
            status=504,
        )

    # ── network / connection ──────────────────────────────────────────────
    if any(kw in msg for kw in ("connection reset", "connection refused", "network")):
        return YoutubeExtractionError(
            "A network error occurred while contacting YouTube.  Please try again.",
            status=503,
        )

    # ── fallback ──────────────────────────────────────────────────────────
    log.debug("Unclassified YouTube error: %s", err)
    return YoutubeExtractionError(
        "Could not fetch this video.  It may be private, restricted, or unavailable.",
        status=400,
    )