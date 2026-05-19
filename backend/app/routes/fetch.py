"""POST /api/fetch — extract video metadata and produce per-format tokens."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.middleware.rate_limit import FETCH_RATE, limiter
from app.schemas import FetchRequest
from app.services.extractor import ExtractionError, extract
from app.services.token_store import token_store
from app.utils.validators import InvalidURLError, validate_url

log = logging.getLogger("clipfetch.fetch")

router = APIRouter()


@router.post("/fetch")
@limiter.limit(FETCH_RATE)
async def fetch_video(request: Request):
    # Parse body manually so we can return our own clean error shape
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Request body must be valid JSON."},
        )
    try:
        payload = FetchRequest(**(body or {}))
    except ValidationError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Please provide a valid URL."},
        )

    try:
        clean_url, platform = validate_url(str(payload.url))
    except InvalidURLError as e:
        return JSONResponse(status_code=400, content={"success": False, "message": str(e)})

    try:
        info = await extract(clean_url, platform)
    except ExtractionError as e:
        return JSONResponse(status_code=e.status, content={"success": False, "message": e.message})
    except Exception:  # noqa: BLE001
        log.exception("Extraction failed for platform=%s", platform)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Could not fetch this video. Please try again."},
        )

    raw_formats = info.pop("raw_formats", [])
    suggested_base = info.pop("suggested_filename_base", "video")

    # Mint a token per format so the response carries no internal URLs.
    formats_out = []
    for f in raw_formats:
        if not f.get("formatId"):
            continue
        token = await token_store.put(
            url=clean_url,
            format_id=f["formatId"],
            platform=platform,
            ext=f.get("ext", "mp4"),
            suggested_filename=f"{suggested_base}.{f.get('ext') or 'mp4'}",
        )
        formats_out.append(
            {
                "formatId": f["formatId"],
                "quality": f["quality"],
                "ext": f["ext"],
                "size": f.get("size"),
                "hasAudio": f["hasAudio"],
                "hasVideo": f["hasVideo"],
                "note": f.get("note"),
                "downloadUrl": f"/api/download?token={token}",
            }
        )

    if not formats_out:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "No downloadable formats were found for this video."},
        )

    return {
        "success": True,
        "platform": platform,
        "title": info["title"],
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "formats": formats_out,
    }
