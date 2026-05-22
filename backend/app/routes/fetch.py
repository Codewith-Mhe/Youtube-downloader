"""POST /api/fetch — extract video metadata and produce one token per tier."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.middleware.rate_limit import FETCH_RATE, limiter
from app.schemas import FetchRequest
from app.services.extractor import (
    TIER_LABELS,
    ExtractionError,
    extract_metadata,
)
from app.services.token_store import token_store
from app.utils.validators import InvalidURLError, validate_url

log = logging.getLogger("clipfetch.fetch")

router = APIRouter()


@router.post("/fetch")
@limiter.limit(FETCH_RATE)
async def fetch_video(request: Request):
    # Parse JSON body manually so we control the error shape
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
        return JSONResponse(
            status_code=400, content={"success": False, "message": str(e)}
        )

    try:
        info = await extract_metadata(clean_url, platform)
    except ExtractionError as e:
        return JSONResponse(
            status_code=e.status, content={"success": False, "message": e.message}
        )
    except Exception:  # noqa: BLE001
        log.exception("Metadata extraction failed for platform=%s", platform)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Could not fetch this video. Please try again.",
            },
        )

    tiers = info.get("tiers") or []
    if not tiers:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "No downloadable quality found for this video.",
            },
        )

    # Mint one opaque token per available tier. The token is the only
    # identifier the frontend ever sees.
    qualities = []
    for tier in tiers:
        token = await token_store.put(url=clean_url, tier=tier, platform=platform)
        qualities.append(
            {
                "id": tier,
                "label": TIER_LABELS.get(tier, tier),
                "downloadUrl": f"/api/download?token={token}",
            }
        )

    return {
        "success": True,
        "platform": platform,
        "title": info["title"],
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "qualities": qualities,
    }
