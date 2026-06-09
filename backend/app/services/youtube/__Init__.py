"""app.services.youtube — YouTube downloader package for ClipFetch.

Public surface (everything else is an implementation detail):

    from app.services.youtube import (
        is_youtube_url,
        extract_metadata,
        download_to_tempfile,
        YoutubeExtractionError,
        TIER_LABELS,
    )
"""
from app.services.youtube.errors import YoutubeExtractionError
from app.services.youtube.extractor import (
    TIER_LABELS,
    download_to_tempfile,
    extract_metadata,
    is_youtube_url,
)

__all__ = [
    "YoutubeExtractionError",
    "TIER_LABELS",
    "download_to_tempfile",
    "extract_metadata",
    "is_youtube_url",
]