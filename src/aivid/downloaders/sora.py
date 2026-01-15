"""Sora video downloader.

Note: OpenAI Sora (sora.com) does not have a public API for video downloads.
Videos can only be downloaded by their creators or via shared links.

Options for future implementation:
1. Direct MP4 link download (if user provides direct link)
2. Browser automation via Playwright (requires authentication)
3. Third-party downloaders (may have ToS concerns)

Current implementation:
- Supports direct MP4 URL downloads only
- Browser automation is experimental and disabled by default
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from typing import ClassVar
from urllib.parse import urlparse

from aivid.config import get_config
from aivid.models.source import SourceInfo, SourcePlatform
from aivid.utils.url_parser import parse_sora_url

from .base import BaseDownloader, DownloadError


class SoraDownloader(BaseDownloader):
    """Download videos from Sora/ChatGPT.

    Currently supports:
    - Direct MP4 URL downloads
    - Shared video links (experimental)

    Requires:
    - httpx for direct downloads
    - playwright (optional) for browser automation
    """

    name: ClassVar[str] = "sora"
    platform: ClassVar[SourcePlatform] = SourcePlatform.SORA

    @classmethod
    def is_available(cls) -> bool:
        """Check if required dependencies are available."""
        try:
            import httpx  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if URL is a Sora/ChatGPT video."""
        # Check for direct MP4 links
        if url.lower().endswith(".mp4"):
            parsed = urlparse(url)
            if "sora.com" in parsed.netloc or "chatgpt.com" in parsed.netloc:
                return True

        # Check for share links
        return cls.extract_video_id(url) is not None

    @classmethod
    def extract_video_id(cls, url: str) -> str | None:
        """Extract video/share ID from Sora URL."""
        return parse_sora_url(url)

    def download(self, url: str, output_dir: str | None = None) -> tuple[str, SourceInfo]:
        """Download Sora video.

        Args:
            url: Sora video URL or direct MP4 link
            output_dir: Directory to save file

        Returns:
            Tuple of (file_path, SourceInfo)

        Raises:
            DownloadError: If download fails
        """
        # Check if it's a direct MP4 link
        if url.lower().endswith(".mp4"):
            return self._download_direct(url, output_dir)

        # For share links, we need browser automation or API access
        # which is currently not publicly available
        raise DownloadError(
            "Sora share link download requires browser authentication. "
            "Please use the 'Copy Link' feature in Sora app to get a direct "
            "download link, or download the video manually and analyze locally."
        )

    def _download_direct(self, url: str, output_dir: str | None = None) -> tuple[str, SourceInfo]:
        """Download direct MP4 link.

        Args:
            url: Direct MP4 URL
            output_dir: Directory to save file

        Returns:
            Tuple of (file_path, SourceInfo)
        """
        try:
            import httpx
        except ImportError as e:
            raise DownloadError("httpx not installed. Run: pip install httpx") from e

        config = get_config()
        output_dir = output_dir or config.download.temp_dir or tempfile.gettempdir()

        video_id = self.extract_video_id(url) or "sora_video"
        output_path = f"{output_dir}/sora_{video_id}.mp4"

        try:
            with httpx.Client(timeout=config.download.timeout_seconds) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Check file size
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > config.download.max_file_size_mb:
                        raise DownloadError(
                            f"File too large: {size_mb:.1f}MB "
                            f"(max: {config.download.max_file_size_mb}MB)"
                        )

                with open(output_path, "wb") as f:
                    f.write(response.content)

                source_info = SourceInfo(
                    platform=SourcePlatform.SORA,
                    original_url=url,
                    video_id=video_id,
                    downloaded_path=output_path,
                    download_timestamp=datetime.now(),
                )

                return output_path, source_info

        except httpx.HTTPError as e:
            raise DownloadError(f"HTTP error downloading Sora video: {e}") from e
        except Exception as e:
            raise DownloadError(f"Error downloading Sora video: {e}") from e
