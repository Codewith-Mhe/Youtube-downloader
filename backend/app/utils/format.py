"""Small formatting helpers."""
from __future__ import annotations

from typing import Optional


def format_duration(seconds: Optional[float]) -> Optional[str]:
    """Format seconds as HH:MM:SS or MM:SS."""
    if seconds is None:
        return None
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return None
    if s < 0:
        return None
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_size(num_bytes: Optional[float]) -> Optional[str]:
    """Human-readable size, e.g. 45.3MB."""
    if num_bytes is None:
        return None
    try:
        b = float(num_bytes)
    except (TypeError, ValueError):
        return None
    if b <= 0:
        return None
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f}{unit}" if unit != "B" else f"{int(b)}{unit}"
        b /= 1024
    return f"{b:.1f}PB"
