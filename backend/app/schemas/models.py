"""Pydantic schemas for request validation and response shaping."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

Platform = Literal["youtube", "tiktok", "twitter", "facebook"]


class FetchRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL to a supported video.")


class VideoFormat(BaseModel):
    formatId: str
    quality: str
    ext: str
    size: Optional[str] = None
    hasAudio: bool
    hasVideo: bool
    downloadUrl: str
    note: Optional[str] = None


class FetchSuccess(BaseModel):
    success: Literal[True] = True
    platform: Platform
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    uploader: Optional[str] = None
    formats: List[VideoFormat]


class FetchError(BaseModel):
    success: Literal[False] = False
    message: str
