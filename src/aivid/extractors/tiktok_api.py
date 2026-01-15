"""TikTok Research API extractor for AI content labels.

This extractor queries the TikTok Research API to check if a video
has been labeled as AI-generated content (AIGC).

API Field: video_tag.type == "AIGC Type"
- video_tag.number == 1: Creator labeled as AI-generated
- video_tag.number == 2: Platform auto-detected AI content

Requirements:
- TikTok Research API access (restricted to approved researchers)
- Client key and secret (set via AIVID_TIKTOK_CLIENT_KEY and AIVID_TIKTOK_CLIENT_SECRET)
- httpx library (pip install httpx)

Reference:
https://developers.tiktok.com/doc/research-api-specs-query-videos

Note: TikTok Research API requires application approval and is only
available to academic and research applications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from aivid.config import get_config
from aivid.extractors.base import BaseExtractor
from aivid.models import AISignal, VideoMetadata

if TYPE_CHECKING:
    pass


class TikTokAPIExtractor(BaseExtractor):
    """Extract AI content labels from TikTok Research API.

    This extractor runs early (priority 5) to check the official
    TikTok Research API for AIGC labels before file-based analysis.

    Note: Requires approved Research API access. The unofficial TikTokApi
    package does not expose the video_tag field.
    """

    name: ClassVar[str] = "tiktok-api"
    priority: ClassVar[int] = 5  # Run very early

    AUTH_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    QUERY_URL = "https://open.tiktokapis.com/v2/research/video/query/"

    @classmethod
    def is_available(cls) -> bool:
        """Check if TikTok API credentials are configured and httpx is available."""
        try:
            import httpx  # noqa: F401
        except ImportError:
            return False

        config = get_config()
        return (
            config.api_keys.tiktok_client_key is not None
            and config.api_keys.tiktok_client_secret is not None
        )

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Query TikTok API for AI content labels.

        This method checks:
        1. If the video has source info indicating it's from TikTok
        2. If not, tries to extract video_id from filename or embedded metadata

        Args:
            path: Path to the video file
            metadata: VideoMetadata object to populate
        """
        # Try to get video_id from source info or embedded metadata
        video_id = self._get_video_id(path, metadata)
        if not video_id:
            return

        self._query_api(video_id, metadata)

    def _get_video_id(self, path: str, metadata: VideoMetadata) -> str | None:
        """Extract TikTok video ID from source info or metadata.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object

        Returns:
            TikTok video ID (numeric string) or None
        """
        # Check if we have source info from download
        if hasattr(metadata, "source") and metadata.source:
            from aivid.models.source import SourcePlatform

            if metadata.source.platform == SourcePlatform.TIKTOK:
                return metadata.source.video_id

        # Check platform AIGC metadata (may have been extracted by ExifTool)
        if metadata.provenance.platform_aigc.tiktok_video_id:
            # Format is typically "vid:xxxxx", extract the ID part
            vid = metadata.provenance.platform_aigc.tiktok_video_id
            if vid.startswith("vid:"):
                return vid[4:]
            return vid

        # Try to extract from filename (common pattern: tiktok_VIDEO_ID.mp4)
        import re
        from pathlib import Path

        filename = Path(path).stem
        # TikTok video IDs are numeric
        match = re.search(r"(\d{15,25})", filename)
        if match:
            return match.group(1)

        return None

    def _get_access_token(self) -> str | None:
        """Get OAuth2 access token for TikTok Research API.

        Returns:
            Access token string or None if authentication fails
        """
        import httpx

        config = get_config()

        try:
            response = httpx.post(
                self.AUTH_URL,
                data={
                    "client_key": config.api_keys.tiktok_client_key,
                    "client_secret": config.api_keys.tiktok_client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            token = data.get("access_token")
            return str(token) if token else None
        except httpx.HTTPError:
            return None

    def _query_api(self, video_id: str, metadata: VideoMetadata) -> None:
        """Query TikTok Research API and update metadata.

        Args:
            video_id: TikTok video ID
            metadata: VideoMetadata object to populate
        """
        import httpx

        access_token = self._get_access_token()
        if not access_token:
            return

        try:
            response = httpx.post(
                self.QUERY_URL,
                params={"fields": "id,video_tag"},
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "query": {"and": [{"field_name": "video_id", "field_values": [video_id]}]},
                    "max_count": 1,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            videos = data.get("data", {}).get("videos", [])
            if not videos:
                return  # Video not found

            video = videos[0]
            video_tag = video.get("video_tag", {})

            # Update platform AIGC info
            platform_aigc = metadata.provenance.platform_aigc
            platform_aigc.tiktok_api_video_tag_number = video_tag.get("number")
            platform_aigc.tiktok_api_video_tag_type = video_tag.get("type")

            # If TikTok says it's AI-generated, update AI detection
            if platform_aigc.is_tiktok_api_ai_labeled:
                self._update_ai_detection(metadata, video_id, video_tag)

        except httpx.HTTPError:
            # Graceful degradation - API errors don't fail the extraction
            pass

    def _update_ai_detection(
        self, metadata: VideoMetadata, video_id: str, video_tag: dict[str, Any]
    ) -> None:
        """Update AI detection based on TikTok API label.

        Args:
            metadata: VideoMetadata object
            video_id: TikTok video ID
            video_tag: video_tag object from API
        """
        ai = metadata.ai_detection
        ai.is_ai_generated = True

        # Determine label source
        tag_number = video_tag.get("number", 0)
        label_source = "creator labeled" if tag_number == 1 else "platform detected"

        # Add signal with high confidence - this is an official platform label
        ai.signals["tiktok_api_aigc"] = AISignal(
            name="TikTok API AIGC Label",
            detected=True,
            confidence=0.99,
            description=f"TikTok API: video_tag.type=AIGC Type ({label_source}, video: {video_id})",
            is_fact=True,  # Direct platform declaration, not inference
        )
