"""Source information models for URL-based analysis."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourcePlatform(str, Enum):
    """Supported video source platforms."""

    LOCAL = "local"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    SORA = "sora"
    UNKNOWN = "unknown"


class SourceInfo(BaseModel):
    """Information about the video source.

    Tracks where a video came from when downloaded from a URL,
    including platform-specific metadata retrieved during download.
    """

    platform: SourcePlatform = SourcePlatform.LOCAL
    original_url: str | None = None
    video_id: str | None = None

    # Download info
    downloaded_path: str | None = None
    download_timestamp: datetime | None = None

    # Platform-specific metadata retrieved during download
    uploader: str | None = None
    uploader_id: str | None = None
    upload_date: datetime | None = None
    title: str | None = None
    description: str | None = None
    duration_seconds: float | None = None

    # Engagement metrics (if available)
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None

    # Tags/categories
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

    @property
    def is_from_url(self) -> bool:
        """Check if video was downloaded from URL."""
        return self.platform != SourcePlatform.LOCAL

    @property
    def platform_url(self) -> str | None:
        """Get the canonical platform URL for this video."""
        if not self.video_id:
            return self.original_url

        if self.platform == SourcePlatform.YOUTUBE:
            return f"https://www.youtube.com/watch?v={self.video_id}"
        if self.platform == SourcePlatform.TIKTOK:
            return f"https://www.tiktok.com/video/{self.video_id}"
        if self.platform == SourcePlatform.SORA:
            return f"https://sora.com/{self.video_id}"

        return self.original_url
