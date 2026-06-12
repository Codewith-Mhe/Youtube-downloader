"""YouTube downloader service — ClipFetch.

Handles:
  - Standard watch URLs: https://www.youtube.com/watch?v=...
  - Short URLs:          https://youtu.be/...
  - YouTube Shorts:     https://www.youtube.com/shorts/...
  - Mobile URLs:        https://m.youtube.com/watch?v=...
  - Live / premiere VODs (best-effort)

This module is entirely independent of app/services/extractor.py.
It imports nothing from the TikTok / X / Facebook extractor and has no
shared mutable state with it.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.services.youtube.cookies import resolve_cookies_path
from app.services.youtube.errors import YoutubeExtractionError, classify_youtube_error
from app.utils.format import format_duration

log = logging.getLogger("clipfetch.youtube")

# ── Tunables ─────────────────────────────────────────────────────────────────
EXTRACT_TIMEOUT = float(os.getenv("YT_EXTRACT_TIMEOUT_SECONDS", "30"))
DOWNLOAD_TIMEOUT = float(os.getenv("YT_DOWNLOAD_TIMEOUT_SECONDS", "300"))
YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip()

# ── Capability detection (once at import time) ────────────────────────────────
FFMPEG_PATH = shutil.which("ffmpeg")
FFMPEG_AVAILABLE = FFMPEG_PATH is not None

if FFMPEG_AVAILABLE:
    log.info("YouTube service: ffmpeg detected at %s", FFMPEG_PATH)
else:
    log.warning(
        "YouTube service: ffmpeg NOT found.  High-quality downloads that require "
        "merging separate video+audio streams will be unavailable.  "
        "Install ffmpeg for 1080p/720p with full audio."
    )

UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# ── Quality tier definitions ───────────────────────────────────────────────────
TIER_LABELS: Dict[str, str] = {
    "best":  "Best available",
    "1080p": "1080p",
    "720p":  "720p",
    "480p":  "480p",
    "360p":  "360p",
    "audio": "Audio only (M4A)",
}

TIER_ORDER: List[str] = ["best", "1080p", "720p", "480p", "360p", "audio"]

# MIME types used when streaming the download to the client.
_CONTENT_TYPES: Dict[str, str] = {
    "mp4":  "video/mp4",
    "webm": "video/webm",
    "mkv":  "video/x-matroska",
    "m4a":  "audio/mp4",
    "mp3":  "audio/mpeg",
    "ogg":  "audio/ogg",
}


# ── URL detection ─────────────────────────────────────────────────────────────

def is_youtube_url(url: str) -> bool:
    """Return True if *url* looks like a YouTube link we should handle."""
    lower = url.lower()
    return any(
        host in lower
        for host in (
            "youtube.com/",
            "youtu.be/",
            "m.youtube.com/",
            "music.youtube.com/",
        )
    )


def _normalize_youtube_url(url: str) -> str:
    """Canonicalize mobile / alternate YouTube hostnames to www.youtube.com.

    yt-dlp handles all of these itself, but canonicalizing early makes logs
    cleaner and avoids edge-cases in extractor selection.
    """
    return (
        url.replace("://m.youtube.com/", "://www.youtube.com/")
           .replace("://music.youtube.com/", "://www.youtube.com/")
    )


# ── yt-dlp option builders ────────────────────────────────────────────────────

def _base_yt_opts() -> Dict[str, Any]:
    """Common yt-dlp options for YouTube requests."""
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 5,
        "extractor_retries": 2,
        "concurrent_fragment_downloads": 3,
        "geo_bypass": True,
        "force_ipv4": True,
        "nocheckcertificate": False,
        "http_headers": {
            "User-Agent": UA_DESKTOP,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "*/*",
        },
        # Prefer the TV and iOS clients — they are less aggressively
        # fingerprinted than the web client and handle Shorts well.
        "extractor_args": {
        "youtube": {
        "player_client": ["web", "tv", "ios"],
        "player_skip": ["webpage", "configs"],
        "po_token": ["web+auto"],  # experimental — helps bypass bot detection
    }
    },
    }

    cookies_path = resolve_cookies_path()
    if cookies_path:
        opts["cookiefile"] = cookies_path
        log.debug("YouTube: using cookies file %s", cookies_path)

    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY

    return opts


def _format_selector(tier: str) -> str:
    """Map a UI quality tier to a yt-dlp format selector string.

    When ffmpeg is available we request separate video+audio streams that
    yt-dlp merges into MP4.  Without ffmpeg we fall back to pre-merged
    single-file formats so something always downloads.
    """
    if tier == "audio":
        if FFMPEG_AVAILABLE:
            return "bestaudio[ext=m4a]/bestaudio/best"
        # Without ffmpeg we cannot extract audio reliably; return a small video.
        return "best[ext=mp4]/best"

    if tier == "best":
        if FFMPEG_AVAILABLE:
            return (
                "bestvideo*[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
                "/bestvideo*+bestaudio"
                "/best[ext=mp4]"
                "/best"
            )
        return "best[ext=mp4]/best"

    try:
        h = int(tier.rstrip("p"))
    except ValueError:
        return "best"

    if FFMPEG_AVAILABLE:
        return (
            f"bestvideo*[height<={h}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
            f"/bestvideo*[height<={h}]+bestaudio"
            f"/best[height<={h}][ext=mp4]"
            f"/best[height<={h}]"
            f"/best"
        )
    return f"best[height<={h}][ext=mp4]/best[height<={h}]/best[ext=mp4]/best"


# ── Tier / metadata helpers ───────────────────────────────────────────────────

def _available_tiers(formats: List[Dict[str, Any]]) -> List[str]:
    """Infer which quality tiers are available from the raw yt-dlp format list."""
    heights = {
        f.get("height")
        for f in formats
        if isinstance(f.get("height"), int) and f.get("height") > 0
    }
    max_h = max(heights) if heights else 0
    has_audio = any(
        f.get("acodec") not in (None, "none") for f in formats
    )

    tiers: List[str] = ["best"]
    for h in (1080, 720, 480, 360):
        if max_h >= h:
            tiers.append(f"{h}p")

    # Offer audio-only only when ffmpeg is present (needed for extraction).
    if has_audio and FFMPEG_AVAILABLE:
        tiers.append("audio")

    return tiers


def _estimate_filesize(formats: List[Dict[str, Any]], tier: str) -> Optional[int]:
    """Return a rough estimated file size in bytes for the given tier, or None.

    We look at the best matching format's reported filesize / filesize_approx
    fields.  For merged formats we sum video + audio estimates.  This is
    best-effort — YouTube often omits these fields.
    """
    if tier == "audio":
        audio_formats = [
            f for f in formats if f.get("acodec") not in (None, "none")
            and f.get("vcodec") in (None, "none")
        ]
        if not audio_formats:
            return None
        best_audio = max(
            audio_formats,
            key=lambda f: f.get("abr") or f.get("tbr") or 0,
        )
        return best_audio.get("filesize") or best_audio.get("filesize_approx")

    try:
        target_h: Optional[int] = None if tier == "best" else int(tier.rstrip("p"))
    except ValueError:
        return None

    video_formats = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and (target_h is None or (f.get("height") or 0) <= target_h)
    ]
    if not video_formats:
        return None

    best_video = max(
        video_formats,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
    )
    audio_formats = [
        f for f in formats
        if f.get("acodec") not in (None, "none")
        and f.get("vcodec") in (None, "none")
    ]
    best_audio = (
        max(audio_formats, key=lambda f: f.get("abr") or f.get("tbr") or 0)
        if audio_formats else None
    )

    video_size = best_video.get("filesize") or best_video.get("filesize_approx")
    audio_size = (
        (best_audio.get("filesize") or best_audio.get("filesize_approx"))
        if best_audio else None
    )

    if video_size and audio_size:
        return video_size + audio_size
    return video_size or audio_size


def _safe_basename(title: str) -> str:
    base = "".join(
        c for c in (title or "video") if c.isalnum() or c in " -_."
    ).strip()
    return (base[:80] or "video").rstrip(".")


# ── Core sync workers (run in thread pool) ────────────────────────────────────

def _extract_metadata_sync(url: str) -> Dict[str, Any]:
    opts = _base_yt_opts()
    opts["skip_download"] = True

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except YoutubeExtractionError:
        raise
    except (DownloadError, ExtractorError) as e:
        raise classify_youtube_error(e) from e
    except Exception as e:  # noqa: BLE001
        log.warning("Unexpected yt-dlp metadata error: %s", e)
        raise classify_youtube_error(e) from e

    if info is None:
        raise YoutubeExtractionError("No information returned for this URL.", status=404)

    # If a playlist URL sneaked through, grab the first entry.
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            raise YoutubeExtractionError("No playable video at this URL.", status=404)
        info = entries[0]

    return info


def _download_sync(url: str, tier: str) -> Tuple[Path, str, str]:
    """Download to a temp directory and return (file_path, filename, content_type)."""
    selector = _format_selector(tier)
    tmpdir = Path(tempfile.mkdtemp(prefix="clipfetch_yt_"))

    opts = _base_yt_opts()
    opts.update(
        {
            "format": selector,
            "outtmpl": str(tmpdir / "%(title).80s.%(ext)s"),
            "restrictfilenames": True,
            "noprogress": True,
            "overwrites": True,
        }
    )

    if tier == "audio" and FFMPEG_AVAILABLE:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ]
    elif FFMPEG_AVAILABLE:
        opts["merge_output_format"] = "mp4"
    # No ffmpeg → no postprocessor; selector chain already restricts to
    # pre-merged single-file formats.

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except YoutubeExtractionError:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except (DownloadError, ExtractorError) as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise classify_youtube_error(e) from e
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("yt-dlp YouTube download failed")
        raise classify_youtube_error(e) from e

    if info is None:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise YoutubeExtractionError("Download returned no info.", status=502)

    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise YoutubeExtractionError("Nothing playable at this URL.", status=404)
        info = entries[0]

    candidates = [p for p in tmpdir.iterdir() if p.is_file()]
    if not candidates:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise YoutubeExtractionError("Downloaded file not found on disk.", status=502)

    # Pick the largest file in case yt-dlp left temp fragments around.
    final = max(candidates, key=lambda p: p.stat().st_size)
    for p in candidates:
        if p != final:
            p.unlink(missing_ok=True)

    ext = final.suffix.lstrip(".").lower() or "mp4"
    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    filename = f"{_safe_basename(info.get('title') or 'video')}.{ext}"
    return final, filename, content_type


# ── Public async API ──────────────────────────────────────────────────────────

async def extract_metadata(url: str) -> Dict[str, Any]:
    """Extract YouTube video metadata. Returns a dict compatible with the
    existing ClipFetch /api/fetch response shape."""
    url = _normalize_youtube_url(url)
    try:
        info = await asyncio.wait_for(
            asyncio.to_thread(_extract_metadata_sync, url),
            timeout=EXTRACT_TIMEOUT,
        )
    except asyncio.TimeoutError as e:
        raise YoutubeExtractionError(
            "Timed out while fetching video info from YouTube.  Please try again.",
            status=504,
        ) from e

    formats: List[Dict[str, Any]] = info.get("formats") or []
    tiers = _available_tiers(formats)

    # Build per-tier estimated file sizes (shown in the UI quality picker).
    size_estimates: Dict[str, Optional[int]] = {
        tier: _estimate_filesize(formats, tier) for tier in tiers
    }

    return {
        "platform": "youtube",
        "title": info.get("title") or "Untitled",
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader") or info.get("channel"),
        "tiers": tiers,
        "size_estimates": size_estimates,  # extra field; frontend ignores unknown keys
        "normalized_url": url,
    }


async def download_to_tempfile(
    url: str, tier: str
) -> Tuple[Path, str, str]:
    """Download a YouTube video to a temp file.

    Returns (path, filename, content_type) — same contract as the existing
    extractor.download_to_tempfile so the download route needs no changes.
    """
    url = _normalize_youtube_url(url)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_download_sync, url, tier),
            timeout=DOWNLOAD_TIMEOUT,
        )
    except asyncio.TimeoutError as e:
        raise YoutubeExtractionError(
            "YouTube download timed out.  Try a lower quality tier.",
            status=504,
        ) from e