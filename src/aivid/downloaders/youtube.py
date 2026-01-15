"""YouTube video downloader using yt-dlp."""

from __future__ import annotations

import tempfile
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from aivid.config import get_config
from aivid.models.source import SourceInfo, SourcePlatform
from aivid.utils.url_parser import parse_youtube_url

from .base import BaseDownloader, DownloadError

if TYPE_CHECKING:
    pass


class YouTubeDownloader(BaseDownloader):
    """Download videos from YouTube using yt-dlp.

    Requires: pip install yt-dlp
    """

    name: ClassVar[str] = "youtube"
    platform: ClassVar[SourcePlatform] = SourcePlatform.YOUTUBE

    @classmethod
    def is_available(cls) -> bool:
        """Check if yt-dlp is available."""
        try:
            import yt_dlp  # noqa: F401

            return True
        except ImportError:
            return False

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return cls.extract_video_id(url) is not None

    @classmethod
    def extract_video_id(cls, url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        return parse_youtube_url(url)

    def download(self, url: str, output_dir: str | None = None) -> tuple[str, SourceInfo]:
        """Download YouTube video.

        Args:
            url: YouTube video URL
            output_dir: Directory to save file

        Returns:
            Tuple of (file_path, SourceInfo)

        Raises:
            DownloadError: If download fails
        """
        try:
            import yt_dlp
        except ImportError as e:
            raise DownloadError("yt-dlp not installed. Run: pip install yt-dlp") from e

        video_id = self.extract_video_id(url)
        if not video_id:
            raise DownloadError(f"Invalid YouTube URL: {url}")

        config = get_config()
        output_dir = output_dir or config.download.temp_dir or tempfile.gettempdir()
        output_template = f"{output_dir}/%(id)s.%(ext)s"

        ydl_opts = {
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": config.download.timeout_seconds,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise DownloadError(f"Failed to extract info from: {url}")

                downloaded_path = ydl.prepare_filename(info)

                source_info = SourceInfo(
                    platform=SourcePlatform.YOUTUBE,
                    original_url=url,
                    video_id=video_id,
                    downloaded_path=downloaded_path,
                    download_timestamp=datetime.now(),
                    uploader=info.get("uploader"),
                    uploader_id=info.get("uploader_id"),
                    upload_date=self._parse_date(info.get("upload_date")),
                    title=info.get("title"),
                    description=info.get("description"),
                    duration_seconds=info.get("duration"),
                    view_count=info.get("view_count"),
                    like_count=info.get("like_count"),
                    comment_count=info.get("comment_count"),
                    tags=info.get("tags") or [],
                    categories=info.get("categories") or [],
                )

                return downloaded_path, source_info

        except yt_dlp.DownloadError as e:
            raise DownloadError(f"YouTube download failed: {e}") from e
        except Exception as e:
            raise DownloadError(f"Unexpected error downloading: {e}") from e

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parse yt-dlp date format (YYYYMMDD)."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            return None
