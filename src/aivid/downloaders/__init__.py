"""Video downloaders for various platforms.

Supported platforms:
- YouTube (via yt-dlp)
- TikTok (via yt-dlp)
- Sora (browser automation, experimental)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aivid.utils.url_parser import Platform, detect_platform

from .base import BaseDownloader, DownloadError

if TYPE_CHECKING:
    pass


def get_downloader_for_url(url: str) -> BaseDownloader | None:
    """Get the appropriate downloader for a URL.

    Args:
        url: Video URL

    Returns:
        Downloader instance or None if unsupported
    """
    platform = detect_platform(url)

    if platform == Platform.YOUTUBE:
        from .youtube import YouTubeDownloader

        return YouTubeDownloader()

    if platform == Platform.TIKTOK:
        from .tiktok import TikTokDownloader

        return TikTokDownloader()

    if platform == Platform.SORA:
        from .sora import SoraDownloader

        return SoraDownloader()

    return None


def get_available_downloaders() -> list[str]:
    """Get list of available downloader names.

    Returns:
        List of downloader names that are available
    """
    available = []

    try:
        from .youtube import YouTubeDownloader

        if YouTubeDownloader.is_available():
            available.append("youtube")
    except ImportError:
        pass

    try:
        from .tiktok import TikTokDownloader

        if TikTokDownloader.is_available():
            available.append("tiktok")
    except ImportError:
        pass

    try:
        from .sora import SoraDownloader

        if SoraDownloader.is_available():
            available.append("sora")
    except ImportError:
        pass

    return available


__all__ = [
    "BaseDownloader",
    "DownloadError",
    "get_downloader_for_url",
    "get_available_downloaders",
]
