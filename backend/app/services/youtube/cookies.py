"""Cookie file resolution for YouTube.

Render Secret Files are mounted read-only at a fixed path.  yt-dlp needs a
writable path it can stat/lock, so we copy the file to /tmp on first use.
The copy is cached for the process lifetime so we don't re-copy on every
request.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("clipfetch.youtube.cookies")

# Set this env var to the path of your Netscape-format cookies.txt.
# On Render: Settings → Secret Files → /etc/secrets/yt_cookies.txt
# Then: YT_COOKIES_FILE=/etc/secrets/yt_cookies.txt
_ENV_KEY = "YT_COOKIES_FILE"

# Module-level cache: resolved writable path (or None if unavailable).
_resolved: Optional[str] = None
_resolved_checked = False


def resolve_cookies_path() -> Optional[str]:
    """Return a writable path to the YouTube cookies file, or None.

    If the configured path is already writable, return it as-is.
    If it is read-only (e.g. Render Secret Files), copy it to /tmp first.
    Result is cached for the process lifetime.
    """
    global _resolved, _resolved_checked  # noqa: PLW0603
    if _resolved_checked:
        return _resolved

    _resolved_checked = True
    raw = os.getenv(_ENV_KEY, "").strip()
    if not raw:
        log.debug("YT_COOKIES_FILE not set — proceeding without cookies")
        _resolved = None
        return None

    src = Path(raw)
    if not src.is_file():
        log.warning("YT_COOKIES_FILE=%s does not exist or is not a file", raw)
        _resolved = None
        return None

    # Check writeability by attempting a temp file in the same directory.
    try:
        fd, _ = tempfile.mkstemp(dir=src.parent)
        os.close(fd)
        os.unlink(_)
        # Original path is writable — use directly.
        log.info("YouTube cookies: using %s (writable)", raw)
        _resolved = raw
        return _resolved
    except OSError:
        pass  # read-only mount (Render Secret Files) — copy to /tmp

    dest = Path(tempfile.mktemp(prefix="yt_cookies_", suffix=".txt", dir="/tmp"))
    try:
        shutil.copy2(src, dest)
        dest.chmod(0o600)
        log.info("YouTube cookies: copied read-only %s → %s", raw, dest)
        _resolved = str(dest)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to copy cookies file to /tmp: %s", exc)
        _resolved = None

    return _resolved