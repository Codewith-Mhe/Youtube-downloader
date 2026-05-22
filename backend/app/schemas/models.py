"""Pydantic schemas for request validation and response shaping."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

Platform = Literal["youtube", "tiktok", "twitter", "facebook"]
Tier = Literal["best", "1080p", "720p", "480p", "360p", "audio"]


class FetchRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL to a supported video.")


class QualityOption(BaseModel):
    id: Tier
    label: str
    downloadUrl: str


class FetchSuccess(BaseModel):
    success: Literal[True] = True
    platform: Platform
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    uploader: Optional[str] = None
    qualities: List[QualityOption]


class FetchError(BaseModel):
    success: Literal[False] = False
    message: str
