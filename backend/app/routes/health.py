from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/api/health")
async def health_get():
    return {"status": "ok"}


# Handles HEAD requests from UptimeRobot
@router.head("/api/health")
async def health_head():
    return Response(status_code=200)


# Handles HEAD requests from UptimeRobot
@router.head("/api/health")
async def health_head():
    return Response(status_code=200)