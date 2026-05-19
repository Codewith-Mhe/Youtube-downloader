"""
ClipFetch — FastAPI backend entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limit import limiter
from app.routes import download, fetch, health
from app.services.token_store import token_store

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("clipfetch")


# --------------------------------------------------------------------------- #
# App lifecycle
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("ClipFetch starting up")
    await token_store.start_sweeper()
    try:
        yield
    finally:
        await token_store.stop_sweeper()
        log.info("ClipFetch shut down cleanly")


app = FastAPI(
    title="ClipFetch API",
    description="Server-side video extraction for YouTube, TikTok, X, and Facebook.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #
_allowed_origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)

# --------------------------------------------------------------------------- #
# Rate limiter
# --------------------------------------------------------------------------- #
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --------------------------------------------------------------------------- #
# Global exception handler — never leak internals
# --------------------------------------------------------------------------- #
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Something went wrong. Please try again."},
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
app.include_router(health.router)
app.include_router(fetch.router, prefix="/api")
app.include_router(download.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "ClipFetch API",
        "version": "1.0.0",
        "endpoints": ["/api/fetch", "/api/download", "/api/health"],
    }
