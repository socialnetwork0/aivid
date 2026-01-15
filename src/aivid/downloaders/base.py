"""Base downloader class for video platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from aivid.models.source import SourceInfo, SourcePlatform


class DownloadError(Exception):
    """Error during video download."""

    pass


class BaseDownloader(ABC):
    """Abstract base class for video downloaders.

    Subclasses should implement:
    - is_available(): Check if dependencies are installed
    - can_handle(): Check if URL is supported
    - extract_video_id(): Parse video ID from URL
    - download(): Download video and return SourceInfo
    """

    name: ClassVar[str] = "base"
    platform: ClassVar[SourcePlatform] = SourcePlatform.UNKNOWN

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this downloader is available.

        Returns:
            True if all dependencies are installed
        """
        pass

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this downloader can handle the given URL.

        Args:
            url: Video URL

        Returns:
            True if URL is supported by this downloader
        """
        pass

    @classmethod
    @abstractmethod
    def extract_video_id(cls, url: str) -> str | None:
        """Extract video ID from URL.

        Args:
            url: Video URL

        Returns:
            Platform-specific video ID or None
        """
        pass

    @abstractmethod
    def download(self, url: str, output_dir: str | None = None) -> tuple[str, SourceInfo]:
        """Download video and return file path with source info.

        Args:
            url: Video URL
            output_dir: Directory to save file (default: temp dir)

        Returns:
            Tuple of (downloaded_file_path, SourceInfo)

        Raises:
            DownloadError: If download fails
        """
        pass
