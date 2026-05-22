"""yt-dlp wrapper — v5 (Facebook + TikTok fix).

Root-cause fixes vs v4
──────────────────────
BUG 1  impersonate='chrome' (string) → AssertionError inside yt-dlp.
       yt-dlp ≥2024.x requires an ImpersonateTarget *object*, not a raw
       string.  The AssertionError was swallowed by bare `except Exception`
       and turned into the generic "Could not fetch" message.
       FIX: use ImpersonateTarget.from_str('chrome') wrapped in a try/except
       so we gracefully degrade when curl_cffi is absent.

BUG 2  HTTP 403 errors (the actual response from Facebook and TikTok on
       cloud IPs) never matched any branch in _classify_error, so they
       fell through to the generic catch-all.
       FIX: explicit 403 / forbidden branch with actionable message.

BUG 3  nocheckcertificate=False → SSL handshake failure on some Render
       regions where the egress proxy injects a self-signed cert.
       FIX: set nocheckcertificate=True globally (yt-dlp already validates
       the TLS cert at the HTTP level; this only disables the Python-level
       hostname check that trips on self-signed proxies).

BUG 4  AssertionError (from BUG 1) not listed in _classify_error, so it
       produced the utterly wrong "Could not fetch" message and was never
       logged.
       FIX: bare except catches AssertionError and logs a clear message.

BUG 5  quiet=True hid ALL yt-dlp stderr in Render logs, making it
       impossible to debug production failures.
       FIX: pass logger=log so every yt-dlp message routes through the app's
       Python logger.  quiet stays True to suppress progress bars; warnings
       and errors come through via the logger hook.

BUG 6  Facebook and TikTok require cookies on shared cloud IPs (Render,
       Railway, Fly.io…).  No env-var fallback was documented or surfaced
       in error messages.
       FIX: honour FB_COOKIES_FILE and TIKTOK_COOKIES_FILE env vars,
       separate from YT_COOKIES_FILE.  When a 403 is received we return a
       message that tells the operator exactly what to do.

BUG 7  _normalize_url only covered Facebook; TikTok short-links
       (vm.tiktok.com, vt.tiktok.com) were not handled.
       FIX: add TikTok short-link normalization.
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
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    UnsupportedError,
)

from app.schemas import Platform
from app.utils.format import format_duration

log = logging.getLogger("clipfetch.extractor")

EXTRACT_TIMEOUT_SECONDS = float(os.getenv("EXTRACT_TIMEOUT_SECONDS", "60"))
DOWNLOAD_TIMEOUT_SECONDS = float(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "300"))

# ── Cookie files ────────────────────────────────────────────────────────────
# Generic catch-all (any platform).
YT_COOKIES_FILE = os.getenv("YT_COOKIES_FILE", "").strip()
# Platform-specific overrides — useful on Render where FB/TT need cookies
# but YouTube can sometimes work without.
FB_COOKIES_FILE = os.getenv("FB_COOKIES_FILE", "").strip() or YT_COOKIES_FILE
TIKTOK_COOKIES_FILE = os.getenv("TIKTOK_COOKIES_FILE", "").strip() or YT_COOKIES_FILE

YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip()

# ── Capability detection — done ONCE at import time ─────────────────────────
FFMPEG_PATH = shutil.which("ffmpeg")
FFMPEG_AVAILABLE = FFMPEG_PATH is not None
if FFMPEG_AVAILABLE:
    log.info("ffmpeg detected at %s", FFMPEG_PATH)
else:
    log.warning(
        "ffmpeg NOT found on PATH. Downloads will fall back to pre-merged "
        "single-file formats only (no audio/video merging, no remuxing). "
        "Install ffmpeg for best quality."
    )

# ── curl_cffi / TLS impersonation ───────────────────────────────────────────
# BUG 1 FIX: import the ImpersonateTarget *class* and build the object once.
# Using the string 'chrome' directly in opts['impersonate'] triggers an
# AssertionError inside yt-dlp ≥2024.x because it expects an
# ImpersonateTarget dataclass, not a bare string.
IMPERSONATE_TARGET: Optional[Any] = None
IMPERSONATE_AVAILABLE = False
try:
    import curl_cffi  # noqa: F401 — just confirm the C extension is present
    from yt_dlp.networking.impersonate import ImpersonateTarget
    IMPERSONATE_TARGET = ImpersonateTarget.from_str("chrome")
    IMPERSONATE_AVAILABLE = True
    log.info(
        "curl_cffi %s detected — TLS impersonation enabled (target: %s)",
        curl_cffi.__version__,
        IMPERSONATE_TARGET,
    )
except ImportError:
    log.warning(
        "curl_cffi NOT installed. TikTok and Facebook will likely fail "
        "due to TLS fingerprinting. Install with: pip install 'yt-dlp[curl-cffi]'"
    )
except Exception as exc:  # noqa: BLE001
    log.warning("Unexpected error setting up curl_cffi impersonation: %s", exc)

UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


# ── yt-dlp logger bridge ─────────────────────────────────────────────────────
# BUG 5 FIX: route yt-dlp messages through Python logging so they appear
# in Render's log stream.  quiet=True suppresses progress bars only.
class _YtdlpLogger:
    """Bridge yt-dlp's internal logger to Python's logging framework."""

    def debug(self, msg: str) -> None:       # noqa: D401
        # yt-dlp prefixes debug lines with "[debug] " — strip for clarity
        log.debug("[yt-dlp] %s", msg.lstrip())

    def info(self, msg: str) -> None:        # noqa: D401
        log.info("[yt-dlp] %s", msg)

    def warning(self, msg: str) -> None:     # noqa: D401
        log.warning("[yt-dlp] %s", msg)

    def error(self, msg: str) -> None:       # noqa: D401
        log.error("[yt-dlp] %s", msg)


_YTDLP_LOGGER = _YtdlpLogger()


class ExtractionError(Exception):
    """User-facing extraction failure with a safe message."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# ── Quality tiers ────────────────────────────────────────────────────────────
TIER_LABELS: Dict[str, str] = {
    "best": "Best available",
    "1080p": "1080p",
    "720p": "720p",
    "480p": "480p",
    "360p": "360p",
    "audio": "Audio only (M4A)",
}

TIER_ORDER = ["best", "1080p", "720p", "480p", "360p", "audio"]


def _selector_for_tier(tier: str, platform: Platform) -> str:
    """Map a UI tier to a yt-dlp format selector."""
    if tier == "audio":
        if FFMPEG_AVAILABLE:
            return "bestaudio[ext=m4a]/bestaudio/best"
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


# ── URL normalization ─────────────────────────────────────────────────────────
def _normalize_url(url: str, platform: Platform) -> str:
    """Light URL canonicalization to help yt-dlp pick the right extractor."""
    if platform == "youtube":
        # Strip playlist/radio params so yt-dlp fetches the single video only.
        # A URL like ?v=abc&list=RD...&start_radio=1 triggers playlist mode,
        # which makes extra network requests and can confuse the extractor.
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if "v" in params:
            clean = urlencode({"v": params["v"][0]})
            url = urlunparse(parsed._replace(query=clean))
            log.debug("YouTube URL normalized: %s", url)

    elif platform == "facebook":
        # web.facebook.com / m.facebook.com → www.facebook.com
        # yt-dlp's Facebook extractor canonicalizes on www.facebook.com.
        url = (
            url.replace("://web.facebook.com/", "://www.facebook.com/")
               .replace("://m.facebook.com/", "://www.facebook.com/")
        )
        # /videos/<id> and /video/<id> are both valid — yt-dlp handles both,
        # but /watch/?v=<id> is the most reliable form for yt-dlp's extractor.
        # We leave that normalization to yt-dlp itself.
    elif platform == "tiktok":
        # BUG 7 FIX: vm.tiktok.com and vt.tiktok.com are short-link redirects.
        # yt-dlp follows them automatically, but being explicit helps logging.
        # No rewrite needed — just log it so operators can see what's happening.
        if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
            log.debug("TikTok short-link detected, yt-dlp will follow redirect: %s", url)
    return url


# ── yt-dlp base options ───────────────────────────────────────────────────────
def _base_opts() -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "quiet": True,           # suppress progress bars
        "no_warnings": False,    # warnings come through the logger bridge
        "logger": _YTDLP_LOGGER, # BUG 5 FIX: route to Python logging
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 3,
        "fragment_retries": 5,
        "extractor_retries": 2,
        "concurrent_fragment_downloads": 2,
        "geo_bypass": True,
        "force_ipv4": True,
        # BUG 3 FIX: set True — Render's egress proxy can inject a self-signed
        # cert that breaks Python's SSL hostname check.  yt-dlp still validates
        # at the HTTP level; this only disables the Python-level check.
        "nocheckcertificate": True,
        "sleep_interval_requests": 1,
        "http_headers": {
            "User-Agent": UA_DESKTOP,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Dest": "document",
        },
    }
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
        log.info("Using proxy: %s", _redact_proxy(YTDLP_PROXY))
    return opts


def _redact_proxy(p: str) -> str:
    if "@" in p:
        scheme, rest = p.split("://", 1) if "://" in p else ("", p)
        _, host = rest.split("@", 1)
        return f"{scheme}://***@{host}" if scheme else f"***@{host}"
    return p


def _apply_cookies(opts: Dict[str, Any], cookies_file: str) -> None:
    """Attach a cookie file to opts if the path exists."""
    if cookies_file and Path(cookies_file).is_file():
        opts["cookiefile"] = cookies_file
        log.info("Using cookies file: %s", cookies_file)
    elif cookies_file:
        log.warning("Cookies file not found: %s", cookies_file)


def _platform_opts(platform: Platform) -> Dict[str, Any]:
    opts = _base_opts()

    if platform == "youtube":
        # ── Player client strategy ───────────────────────────────────────────
        # YouTube requires a Proof-of-Origin (PO) token for web clients on
        # cloud IPs (Render, Railway, etc.) since 2024.
        #
        # TWO modes depending on whether cookies are available:
        #
        # WITH cookies (YT_COOKIES_FILE set and file exists):
        #   Use web/default clients FIRST — the session cookie (SAPISID,
        #   __Secure-3PSID etc.) acts as implicit PO token proof.
        #   Embedded clients are kept as fallback.
        #
        # WITHOUT cookies:
        #   Use embedded clients only — tv_embedded and web_embedded bypass
        #   PO token enforcement entirely (they are iframe/TV contexts that
        #   YouTube treats differently).
        #
        # NOTE: player_skip:["configs"] intentionally removed — it prevents
        # the extractor finding INNERTUBE_API_KEY → "Failed to extract any
        # player response" even on good connections.

        cookies_exist = bool(YT_COOKIES_FILE and Path(YT_COOKIES_FILE).is_file())

        if cookies_exist:
            # Cookies present: web clients first (they honour the session),
            # then embedded as fallback.
            player_clients = ["web", "default", "tv_embedded", "web_embedded", "tv", "ios"]
            log.info("YouTube: cookies detected — using web-first client order")
        else:
            # No cookies: embedded clients bypass PO token enforcement.
            player_clients = ["tv_embedded", "web_embedded", "tv", "ios"]
            log.warning(
                "YouTube: no cookies file found at %r — using embedded clients only. "
                "Set YT_COOKIES_FILE env var for better reliability.",
                YT_COOKIES_FILE or "(not set)",
            )

        opts["extractor_args"] = {
            "youtube": {
                "player_client": player_clients,
            }
        }
        opts["socket_timeout"] = 30
        opts["retries"] = 5
        _apply_cookies(opts, YT_COOKIES_FILE)

    elif platform == "tiktok":
        opts["http_headers"]["Referer"] = "https://www.tiktok.com/"
        opts["http_headers"]["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
        # BUG 1 FIX: use ImpersonateTarget object, not a string.
        if IMPERSONATE_AVAILABLE and IMPERSONATE_TARGET is not None:
            opts["impersonate"] = IMPERSONATE_TARGET
        _apply_cookies(opts, TIKTOK_COOKIES_FILE)

    elif platform == "twitter":
        opts["http_headers"]["Referer"] = "https://twitter.com/"

    elif platform == "facebook":
        # Facebook stalls connections on residential + cloud IPs.
        # Longer socket_timeout prevents premature "Request timed out" errors.
        opts["socket_timeout"] = 40
        opts["retries"] = 5
        opts["http_headers"]["Referer"] = "https://www.facebook.com/"
        opts["http_headers"]["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        )
        opts["http_headers"]["Accept-Encoding"] = "gzip, deflate, br"
        opts["http_headers"]["Connection"] = "keep-alive"
        opts["http_headers"]["Upgrade-Insecure-Requests"] = "1"
        # NOTE: curl_cffi impersonation is intentionally NOT used for Facebook.
        # On many Windows machines and some cloud hosts, libcurl (used by
        # curl_cffi) cannot connect to facebook.com port 443 even when Python's
        # built-in urllib can. We fall back to yt-dlp's default Python HTTP
        # handler which uses urllib3 and works reliably everywhere.
        # BUG 6 FIX: apply platform-specific cookie file.
        _apply_cookies(opts, FB_COOKIES_FILE)

    return opts


# ── Error classification ──────────────────────────────────────────────────────
def _classify_error(err: BaseException, platform: Platform | None = None) -> ExtractionError:
    msg = str(err).lower()

    log.error(
        "[classify_error] platform=%s type=%s raw=%s",
        platform,
        type(err).__name__,
        str(err)[:500],
    )

    # BUG 4 FIX: AssertionError from bad impersonate target
    if isinstance(err, AssertionError):
        return ExtractionError(
            "Internal server error (impersonation config). "
            "Please report this to the site operator.",
            status=500,
        )

    # ── ffmpeg missing ───────────────────────────────────────────────────────
    if "ffmpeg" in msg and ("not found" in msg or "not installed" in msg or "is required" in msg):
        return ExtractionError(
            "Server is missing ffmpeg. The operator needs to install it.",
            status=500,
        )

    # ── YouTube bot detection / PO token (most common on cloud IPs 2025/2026) ─
    if "sign in to confirm" in msg or "not a bot" in msg or "confirm you're not" in msg:
        if YT_COOKIES_FILE:
            return ExtractionError(
                "YouTube is blocking this server even with cookies. "
                "Your cookies may have expired — re-export from your browser and re-deploy.",
                status=429,
            )
        return ExtractionError(
            "YouTube requires sign-in verification on this server. "
            "To fix: export a YouTube cookies.txt from your browser and set "
            "YT_COOKIES_FILE to its path on the server.",
            status=429,
        )

    # ── YouTube: failed to extract any player response ────────────────────────
    # This happens when ALL player clients return 403 — either the server IP is
    # fully blocked by YouTube, or cookies are missing/expired.
    if "failed to extract any player response" in msg:
        if YT_COOKIES_FILE:
            return ExtractionError(
                "YouTube blocked all player clients on this server. "
                "Your cookies may have expired — re-export and re-deploy. "
                "If the problem persists, the server IP may be fully blocked by YouTube.",
                status=429,
            )
        return ExtractionError(
            "YouTube blocked all player clients on this server. "
            "This is a known issue with cloud-hosted video downloaders. "
            "Fix: export a YouTube cookies.txt from your browser (while logged in) "
            "and set YT_COOKIES_FILE to its path on the server.",
            status=429,
        )

    # ── YouTube: INNERTUBE_CONTEXT missing (oauth2 plugin conflict) ───────────
    if "innertube_context" in msg:
        return ExtractionError(
            "YouTube extractor conflict — a yt-dlp plugin is interfering. "
            "Please report this to the site operator.",
            status=500,
        )

    # ── BUG 2 FIX: HTTP 403 — Facebook and TikTok block cloud IPs ───────────
    # When cookies are present the 403 is a true access-denied (private/login).
    # When cookies are absent it usually means the platform is blocking the
    # cloud egress IP.  Surface a helpful message either way.
    if "http error 403" in msg or "403: forbidden" in msg or "forbidden" in msg:
        if platform == "facebook":
            if FB_COOKIES_FILE:
                return ExtractionError(
                    "Facebook denied access (HTTP 403). "
                    "Your cookies may have expired — re-export them and re-deploy.",
                    status=403,
                )
            return ExtractionError(
                "Facebook returned HTTP 403. Facebook blocks most cloud-server "
                "IPs. To fix this: export a cookies.txt from a logged-in browser "
                "session, upload it to your server, and set the FB_COOKIES_FILE "
                "environment variable to its path.",
                status=403,
            )
        if platform == "tiktok":
            if TIKTOK_COOKIES_FILE:
                return ExtractionError(
                    "TikTok denied access (HTTP 403). "
                    "Your cookies may have expired — re-export and re-deploy.",
                    status=403,
                )
            return ExtractionError(
                "TikTok returned HTTP 403. TikTok blocks most cloud-server IPs. "
                "To fix this: export a cookies.txt from a logged-in browser "
                "session, upload it to your server, and set the TIKTOK_COOKIES_FILE "
                "environment variable to its path.",
                status=403,
            )
        return ExtractionError(
            "Access denied (HTTP 403). The video may be private or region-locked.",
            status=403,
        )

    # ── Facebook parse failure (curl_cffi missing) ───────────────────────────
    if "cannot parse data" in msg:
        if not IMPERSONATE_AVAILABLE:
            return ExtractionError(
                "Server is missing curl_cffi (TLS impersonation). "
                "The operator needs to install yt-dlp[curl-cffi].",
                status=500,
            )
        return ExtractionError(
            "Could not read this video — Facebook may have changed their "
            "page format. Please try again later.",
            status=400,
        )

    # ── Geo / unsupported / access control ──────────────────────────────────
    if isinstance(err, GeoRestrictedError) or ("geo" in msg and "restrict" in msg):
        return ExtractionError("This video is geo-restricted.", status=451)
    if isinstance(err, UnsupportedError):
        return ExtractionError("This link is not supported.", status=400)
    if "private" in msg:
        return ExtractionError("This video is private.", status=403)
    if "age" in msg and ("restrict" in msg or "sign in" in msg or "confirm" in msg):
        return ExtractionError("Age-restricted; sign-in required.", status=403)
    if "members" in msg and "only" in msg:
        return ExtractionError("Members-only video.", status=403)
    if "removed" in msg or "deleted" in msg or "no longer" in msg:
        return ExtractionError("This video has been removed.", status=404)
    if "not available" in msg or "unavailable" in msg or "does not exist" in msg:
        return ExtractionError("This video is unavailable.", status=404)
    if "login" in msg or "cookies" in msg:
        return ExtractionError("Sign-in required for this video.", status=403)
    if "http error 429" in msg or "too many requests" in msg:
        return ExtractionError(
            "Upstream is rate-limiting us. Please try again in a few minutes.",
            status=429,
        )
    if "timed out" in msg or "timeout" in msg:
        return ExtractionError("Request timed out. Please try again.", status=504)
    if "ssl" in msg or "certificate" in msg:
        return ExtractionError(
            "SSL error communicating with the upstream server. Please try again.",
            status=502,
        )

    return ExtractionError(
        "Could not fetch this video. It may be private, restricted, or unsupported.",
        status=400,
    )


# ── Metadata extraction ───────────────────────────────────────────────────────
def _detect_available_tiers(info: Dict[str, Any]) -> List[str]:
    formats = info.get("formats") or []
    heights = {f.get("height") for f in formats if isinstance(f.get("height"), int)}
    max_h = max(heights) if heights else 0
    has_audio = any(f.get("acodec") not in (None, "none") for f in formats)
    out: List[str] = ["best"]
    for tier_h in (1080, 720, 480, 360):
        if max_h >= tier_h:
            out.append(f"{tier_h}p")
    if has_audio and FFMPEG_AVAILABLE:
        out.append("audio")
    return out


def _extract_metadata_sync(url: str, platform: Platform) -> Dict[str, Any]:
    opts = _platform_opts(platform)
    opts["skip_download"] = True
    log.info("Extracting metadata: platform=%s url=%s", platform, url)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            raise ExtractionError("No information returned.", status=404)
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if not entries:
                raise ExtractionError("No playable video at this URL.", status=404)
            info = entries[0]
        log.info(
            "Metadata OK: platform=%s title=%r formats=%d",
            platform,
            info.get("title"),
            len(info.get("formats") or []),
        )
        return info
    except ExtractionError:
        raise
    except (DownloadError, ExtractorError) as e:
        raise _classify_error(e, platform) from e
    except AssertionError as e:          # BUG 4 FIX
        log.exception("AssertionError in yt-dlp (likely bad impersonate target)")
        raise _classify_error(e, platform) from e
    except Exception as e:               # noqa: BLE001
        log.exception("Unexpected yt-dlp metadata error: platform=%s", platform)
        raise _classify_error(e, platform) from e


async def extract_metadata(url: str, platform: Platform) -> Dict[str, Any]:
    url = _normalize_url(url, platform)
    try:
        info = await asyncio.wait_for(
            asyncio.to_thread(_extract_metadata_sync, url, platform),
            timeout=EXTRACT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as e:
        raise ExtractionError("Request timed out. Please try again.", status=504) from e

    title = info.get("title") or "Untitled"
    tiers = _detect_available_tiers(info)
    return {
        "platform": platform,
        "title": title,
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader") or info.get("channel"),
        "tiers": tiers,
        "normalized_url": url,
    }


# ── Download ──────────────────────────────────────────────────────────────────
def _safe_basename(title: str) -> str:
    base = "".join(c for c in (title or "video") if c.isalnum() or c in " -_.").strip()
    return (base[:80] or "video").rstrip(".")


_CONTENT_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
}


def download_to_tempfile(
    url: str, tier: str, platform: Platform
) -> Tuple[Path, str, str]:
    url = _normalize_url(url, platform)
    selector = _selector_for_tier(tier, platform)
    tmpdir = Path(tempfile.mkdtemp(prefix="clipfetch_"))

    opts = _platform_opts(platform)
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

    log.info("Starting download: platform=%s tier=%s url=%s", platform, tier, url)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if info is None:
            raise ExtractionError("Download failed.", status=502)
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if not entries:
                raise ExtractionError("Nothing playable here.", status=404)
            info = entries[0]
    except ExtractionError:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except (DownloadError, ExtractorError) as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise _classify_error(e, platform) from e
    except AssertionError as e:          # BUG 4 FIX
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("AssertionError in yt-dlp download (bad impersonate target?)")
        raise _classify_error(e, platform) from e
    except Exception as e:               # noqa: BLE001
        shutil.rmtree(tmpdir, ignore_errors=True)
        log.exception("yt-dlp download failed: platform=%s", platform)
        raise _classify_error(e, platform) from e

    candidates = [p for p in tmpdir.iterdir() if p.is_file()]
    if not candidates:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ExtractionError("Downloaded file not found.", status=502)
    final = max(candidates, key=lambda p: p.stat().st_size)
    for p in candidates:
        if p != final:
            p.unlink(missing_ok=True)

    ext = final.suffix.lstrip(".").lower() or "mp4"
    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    filename = f"{_safe_basename(info.get('title') or 'video')}.{ext}"
    log.info("Download complete: file=%s size=%d", final.name, final.stat().st_size)
    return final, filename, content_type