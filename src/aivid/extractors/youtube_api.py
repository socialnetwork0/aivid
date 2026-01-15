"""YouTube Data API v3 extractor for AI content labels.

This extractor queries the YouTube Data API to check if a video
has been labeled as containing synthetic/AI-generated media.

API Field: status.containsSyntheticMedia (boolean)

Requirements:
- YouTube Data API key (set via AIVID_YOUTUBE_API_KEY env var or config)
- httpx library (pip install httpx)

Reference:
https://developers.google.com/youtube/v3/docs/videos#status.containsSyntheticMedia
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from aivid.config import get_config
from aivid.extractors.base import BaseExtractor
from aivid.models import AISignal, VideoMetadata

if TYPE_CHECKING:
    pass


class YouTubeAPIExtractor(BaseExtractor):
    """Extract AI content labels from YouTube Data API v3.

    This extractor runs early (priority 5) to check the official
    YouTube API for the containsSyntheticMedia field before
    performing file-based analysis.

    Note: Only works for videos downloaded from YouTube where
    the video_id is known via metadata.source or filename parsing.
    """

    name: ClassVar[str] = "youtube-api"
    priority: ClassVar[int] = 5  # Run very early

    API_URL = "https://www.googleapis.com/youtube/v3/videos"

    @classmethod
    def is_available(cls) -> bool:
        """Check if YouTube API key is configured and httpx is available."""
        try:
            import httpx  # noqa: F401
        except ImportError:
            return False

        config = get_config()
        return config.api_keys.youtube_api_key is not None

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Query YouTube API for AI content labels.

        This method checks:
        1. If the video has source info indicating it's from YouTube
        2. If not, tries to extract video_id from filename (e.g., dQw4w9WgXcQ.mp4)

        Args:
            path: Path to the video file
            metadata: VideoMetadata object to populate
        """
        # Try to get video_id from source info first
        video_id = self._get_video_id(path, metadata)
        if not video_id:
            return

        self._query_api(video_id, metadata)

    def _get_video_id(self, path: str, metadata: VideoMetadata) -> str | None:
        """Extract YouTube video ID from source info or filename.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object

        Returns:
            11-character YouTube video ID or None
        """
        # Check if we have source info from download
        if hasattr(metadata, "source") and metadata.source:
            from aivid.models.source import SourcePlatform

            if metadata.source.platform == SourcePlatform.YOUTUBE:
                return metadata.source.video_id

        # Try to extract from filename (common pattern: VIDEO_ID.mp4)
        import re
        from pathlib import Path

        filename = Path(path).stem
        # YouTube video IDs are exactly 11 characters: [a-zA-Z0-9_-]
        match = re.match(r"^([a-zA-Z0-9_-]{11})$", filename)
        if match:
            return match.group(1)

        # Also check for ID at end of filename (common download pattern)
        match = re.search(r"[_\-\s]([a-zA-Z0-9_-]{11})$", filename)
        if match:
            return match.group(1)

        return None

    def _query_api(self, video_id: str, metadata: VideoMetadata) -> None:
        """Query YouTube API and update metadata.

        Args:
            video_id: YouTube video ID
            metadata: VideoMetadata object to populate
        """
        import httpx

        config = get_config()
        api_key = config.api_keys.youtube_api_key

        try:
            response = httpx.get(
                self.API_URL,
                params={
                    "part": "status",
                    "id": video_id,
                    "key": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("items"):
                return  # Video not found or private

            item = data["items"][0]
            status = item.get("status", {})

            # Update platform AIGC info
            platform_aigc = metadata.provenance.platform_aigc
            platform_aigc.youtube_video_id = video_id
            platform_aigc.youtube_contains_synthetic_media = status.get("containsSyntheticMedia")

            # If YouTube says it's AI-generated, update AI detection
            if platform_aigc.is_youtube_ai_labeled:
                self._update_ai_detection(metadata, video_id)

        except httpx.HTTPError:
            # Graceful degradation - API errors don't fail the extraction
            pass

    def _update_ai_detection(self, metadata: VideoMetadata, video_id: str) -> None:
        """Update AI detection based on YouTube API label.

        Args:
            metadata: VideoMetadata object
            video_id: YouTube video ID for reference
        """
        ai = metadata.ai_detection
        ai.is_ai_generated = True

        # Add signal with high confidence - this is an official platform label
        ai.signals["youtube_api_synthetic"] = AISignal(
            name="YouTube API Synthetic Media",
            detected=True,
            confidence=0.99,
            description=f"YouTube API: containsSyntheticMedia=true (video: {video_id})",
            is_fact=True,  # Direct platform declaration, not inference
        )
