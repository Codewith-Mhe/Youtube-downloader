"""Wrapper around yt-dlp that produces clean, UI-friendly results.

We use yt-dlp purely as a Python library — no subprocess shelling — so there
is no command-injection surface. The URL is validated against an allowlist
before it ever reaches this layer.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    UnsupportedError,
)

from app.schemas import Platform
from app.utils.format import format_duration, format_size

log = logging.getLogger("clipfetch.extractor")

EXTRACT_TIMEOUT_SECONDS = float(os.getenv("EXTRACT_TIMEOUT_SECONDS", "25"))


class ExtractionError(Exception):
    """User-facing extraction failure with a safe message."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- #
# Public types
# --------------------------------------------------------------------------- #
class ExtractedFormat(dict):
    """Plain dict used to ferry data to the route layer (kept JSON-safe)."""


class ExtractedInfo(dict):
    pass


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
_BASE_OPTS: Dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "socket_timeout": 30,
    "extract_flat": False,
    "fragment_retries": 5,
    "nocheckcertificate": False,
    "geo_bypass": True,
    "followredirects": True,
    # Be a polite, modern client
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tiktok.com/",
    },
}


def _ydl_opts(platform: Platform) -> Dict[str, Any]:
    opts = dict(_BASE_OPTS)
    # Tighten format selection a bit per platform. yt-dlp handles each one
    # well; these are just sensible defaults.
    if platform == "youtube":
        opts["youtube_include_dash_manifest"] = True
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["web", "android"],
            }
        }
        opts["cookiefile"] = os.path.join(
            os.path.dirname(__file__), "..", "..", "cookies.txt"
        )
    return opts


def _classify_error(err: BaseException) -> ExtractionError:
    msg = str(err).lower()
    if isinstance(err, GeoRestrictedError) or "geo" in msg and "restrict" in msg:
        return ExtractionError(
            "This video is geo-restricted and cannot be fetched from this server.",
            status=451,
        )
    if isinstance(err, UnsupportedError):
        return ExtractionError(
            "This link is not supported. Please try a different video URL.",
            status=400,
        )
    if "private" in msg:
        return ExtractionError("This video is private.", status=403)
    if "members-only" in msg or "members only" in msg:
        return ExtractionError("This video is members-only and cannot be downloaded.", status=403)
    if "age" in msg and ("restrict" in msg or "confirm" in msg or "sign in" in msg):
        return ExtractionError(
            "This video is age-restricted and cannot be downloaded without sign-in.",
            status=403,
        )
    if "removed" in msg or "deleted" in msg or "no longer available" in msg:
        return ExtractionError("This video has been removed or is no longer available.", status=404)
    if "not available" in msg or "unavailable" in msg:
        return ExtractionError("This video is unavailable.", status=404)
    if "login" in msg or "sign in" in msg or "cookies" in msg:
        return ExtractionError(
            "This video requires sign-in and cannot be downloaded.", status=403
        )
    if "timed out" in msg or "timeout" in msg:
        return ExtractionError("The request timed out. Please try again.", status=504)
    if "http error 429" in msg or "too many requests" in msg:
        return ExtractionError("Upstream is rate-limiting us. Please try again later.", status=429)
    # Default
    return ExtractionError(
        "Could not fetch this video. It may be private, restricted, or unsupported.",
        status=400,
    )


def _safe_filename(title: str, ext: str) -> str:
    base = "".join(c for c in (title or "video") if c.isalnum() or c in (" ", "-", "_")).strip()
    base = base[:80] or "video"
    return f"{base}.{ext or 'mp4'}"


def _build_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pick a clean, deduped list of formats to show the user."""
    raw_formats = info.get("formats") or []
    seen: set[Tuple[Optional[int], Optional[int], str]] = set()
    candidates: List[Dict[str, Any]] = []

    for f in raw_formats:
        # Skip storyboards / manifests / images
        if f.get("vcodec") == "none" and f.get("acodec") == "none":
            continue
        if f.get("ext") in ("mhtml", "jpg", "webp", "png"):
            continue

        has_video = f.get("vcodec") != "none" and bool(f.get("height") or f.get("width") or f.get("vcodec"))
        has_audio = f.get("acodec") not in (None, "none")
        ext = f.get("ext") or ""
        height = f.get("height")
        abr = f.get("abr")

        # Build a quality label
        if has_video:
            if height:
                quality = f"{height}p"
            elif f.get("format_note"):
                quality = str(f["format_note"])
            else:
                quality = "video"
        else:
            quality = f"{int(abr)}kbps audio" if abr else "audio"

        # Deduplicate on (height, abr, ext)
        key = (height, int(abr) if abr else None, ext)
        if key in seen:
            continue
        seen.add(key)

        candidates.append(
            {
                "formatId": str(f.get("format_id") or ""),
                "quality": quality,
                "ext": ext,
                "size": format_size(f.get("filesize") or f.get("filesize_approx")),
                "hasAudio": has_audio,
                "hasVideo": has_video,
                "height": height or 0,
                "abr": abr or 0,
                "note": f.get("format_note"),
            }
        )

    # Sort: video-with-audio first (descending quality), then video-only, then audio-only
    def sort_key(c: Dict[str, Any]) -> Tuple[int, int, int]:
        if c["hasVideo"] and c["hasAudio"]:
            tier = 0
        elif c["hasVideo"]:
            tier = 1
        else:
            tier = 2
        return (tier, -int(c["height"] or 0), -int(c["abr"] or 0))

    candidates.sort(key=sort_key)

    # Limit to a sensible number so the UI stays clean
    return candidates[:12]


def _extract_sync(url: str, platform: Platform) -> Dict[str, Any]:
    """Run yt-dlp in the current (worker) thread."""
    try:
        with yt_dlp.YoutubeDL(_ydl_opts(platform)) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            raise ExtractionError("No information returned for this video.", status=404)


        if info.get("_type") == "url":
            resolved_url = info.get("url")
            if not resolved_url:
                raise ExtractionError("Could not resolve short link.", status=404)
            with yt_dlp.YoutubeDL(_ydl_opts(platform)) as ydl:
                info = ydl.extract_info(resolved_url, download=False)
            if info is None:
                raise ExtractionError("No information returned for this video.", status=404)   
        # If yt-dlp returns a playlist entry, take the first item
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if not entries:
                raise ExtractionError("This link contains no playable video.", status=404)
            info = entries[0]
        return info
    except ExtractionError:
        raise
    except (DownloadError, ExtractorError) as e:
        raise _classify_error(e) from e
    except Exception as e:  # noqa: BLE001
        log.warning("Unexpected yt-dlp error: %s", e)
        raise _classify_error(e) from e


async def extract(url: str, platform: Platform) -> Dict[str, Any]:
    """Async wrapper with a hard timeout."""
    try:
        info = await asyncio.wait_for(
            asyncio.to_thread(_extract_sync, url, platform),
            timeout=EXTRACT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as e:
        raise ExtractionError("Request timed out. Please try again.", status=504) from e

    title = info.get("title") or "Untitled"
    return {
        "platform": platform,
        "title": title,
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader") or info.get("channel"),
        "raw_formats": _build_formats(info),
        "suggested_filename_base": title,
    }


def stream_format(url: str, format_id: str, platform: Platform):
    """Yield bytes for a chosen format. Used by the /download streaming route.

    Streams directly from the source URL resolved by yt-dlp — we never write
    the full file to disk, so there is nothing to clean up.
    """
    import requests  # local import keeps cold-start light

    opts = dict(_ydl_opts(platform))
    opts["format"] = format_id
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except (DownloadError, ExtractorError) as e:
        raise _classify_error(e) from e
    if info is None:
        raise ExtractionError("Could not resolve the requested format.", status=404)
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            raise ExtractionError("Nothing playable at this URL.", status=404)
        info = entries[0]

    direct_url = info.get("url")
    if not direct_url:
        raise ExtractionError("This format is not directly downloadable.", status=400)

    headers = dict(info.get("http_headers") or {})
    # Some platforms reject requests without a User-Agent
    headers.setdefault("User-Agent", _BASE_OPTS["http_headers"]["User-Agent"])

    try:
        resp = requests.get(direct_url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ExtractionError("Upstream download failed. Please try again.", status=502) from e

    def _iter():
        try:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            resp.close()

    return _iter()
