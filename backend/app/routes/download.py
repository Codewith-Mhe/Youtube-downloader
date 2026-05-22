"""GET /api/download?token=... — yt-dlp downloads to temp, we stream, then rm."""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.middleware.rate_limit import DOWNLOAD_RATE, limiter
from app.services.extractor import (
    DOWNLOAD_TIMEOUT_SECONDS,
    ExtractionError,
    download_to_tempfile,
)
from app.services.token_store import token_store

log = logging.getLogger("clipfetch.download")

router = APIRouter()


@router.get("/download")
@limiter.limit(DOWNLOAD_RATE)
async def download(
    request: Request, token: str = Query(..., min_length=8, max_length=128)
):
    ticket = await token_store.get(token)
    if ticket is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Download link has expired. Please fetch the video again.",
            },
        )

    # Run yt-dlp + ffmpeg in a worker thread with a hard timeout. Anything
    # that fails here returns JSON; the FRONTEND must parse the response
    # before triggering a browser download (see fetcher-panel.tsx).
    try:
        path, filename, content_type = await asyncio.wait_for(
            asyncio.to_thread(
                download_to_tempfile, ticket.url, ticket.tier, ticket.platform
            ),
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"success": False, "message": "Download timed out. Please try a lower quality."},
        )
    except ExtractionError as e:
        return JSONResponse(
            status_code=e.status, content={"success": False, "message": e.message}
        )
    except Exception:  # noqa: BLE001
        log.exception("Unexpected download failure")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Download failed. Please try again."},
        )

    size = path.stat().st_size
    tmpdir = path.parent

    def iter_and_cleanup():
        try:
            with path.open("rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    ext = path.suffix.lstrip(".") or "mp4"
    quoted = quote(filename, safe="")
    headers = {
        # ASCII fallback + UTF-8 form for non-ASCII titles
        "Content-Disposition": (
            f'attachment; filename="clipfetch.{ext}"; '
            f"filename*=UTF-8''{quoted}"
        ),
        "Content-Length": str(size),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
        # Tell the browser this is a binary file we are serving as-is
        "Accept-Ranges": "none",
    }
    return StreamingResponse(iter_and_cleanup(), media_type=content_type, headers=headers)
