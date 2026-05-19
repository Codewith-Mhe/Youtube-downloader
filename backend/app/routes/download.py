"""GET /api/download?token=... — stream the chosen format to the user."""
from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.middleware.rate_limit import DOWNLOAD_RATE, limiter
from app.services.extractor import ExtractionError, stream_format
from app.services.token_store import token_store

log = logging.getLogger("clipfetch.download")

router = APIRouter()


_CONTENT_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "mkv": "video/x-matroska",
    "ogg": "audio/ogg",
}


@router.get("/download")
@limiter.limit(DOWNLOAD_RATE)
async def download(request: Request, token: str = Query(..., min_length=8, max_length=128)):
    ticket = await token_store.get(token)
    if ticket is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "This download link has expired. Please fetch the video again."},
        )

    try:
        # Resolve and start streaming in a worker thread to keep the loop free
        import anyio

        iterator = await anyio.to_thread.run_sync(
            stream_format, ticket.url, ticket.format_id, ticket.platform
        )
    except ExtractionError as e:
        return JSONResponse(status_code=e.status, content={"success": False, "message": e.message})
    except Exception:  # noqa: BLE001
        log.exception("Download failed for token=%s", token[:8])
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Download failed. Please try again."},
        )

    content_type = _CONTENT_TYPES.get(ticket.ext.lower(), "application/octet-stream")
    filename = ticket.suggested_filename or f"clipfetch.{ticket.ext or 'mp4'}"
    # RFC 5987 filename encoding to handle non-ASCII titles safely
    quoted = quote(filename, safe="")
    headers = {
        "Content-Disposition": f"attachment; filename=\"clipfetch.{ticket.ext or 'mp4'}\"; filename*=UTF-8''{quoted}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    return StreamingResponse(iterator, media_type=content_type, headers=headers)
