"""URL parsing utilities for video platforms.

Supports:
- YouTube: youtube.com, youtu.be, youtube.com/shorts
- TikTok: tiktok.com/@user/video/xxx, vm.tiktok.com
- Sora: sora.com, chatgpt.com (OpenAI Sora)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    """Supported video platforms."""

    LOCAL = "local"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    SORA = "sora"
    UNKNOWN = "unknown"


@dataclass
class ParsedURL:
    """Result of URL parsing."""

    platform: Platform
    video_id: str | None
    original_url: str
    is_valid: bool = True


# YouTube URL patterns
YOUTUBE_PATTERNS = [
    # Standard watch URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    # Short URLs
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    # Shorts
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    # Embed URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    # v= anywhere in URL (query param)
    r"(?:https?://)?(?:www\.)?youtube\.com/.*[?&]v=([a-zA-Z0-9_-]{11})",
]

# TikTok URL patterns
TIKTOK_PATTERNS = [
    # Standard video URLs
    r"(?:https?://)?(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)",
    # Short URLs (need redirect resolution)
    r"(?:https?://)?vm\.tiktok\.com/([a-zA-Z0-9]+)",
    # Web URLs with video in path
    r"(?:https?://)?(?:www\.)?tiktok\.com/.*/video/(\d+)",
]

# Sora URL patterns
SORA_PATTERNS = [
    # sora.com URLs
    r"(?:https?://)?(?:www\.)?sora\.com/([^/?]+)",
    # ChatGPT shared content (may include Sora videos)
    r"(?:https?://)?chatgpt\.com/share/([a-zA-Z0-9-]+)",
    # ChatGPT gen URLs
    r"(?:https?://)?chatgpt\.com/g/([a-zA-Z0-9-]+)",
]


def parse_youtube_url(url: str) -> str | None:
    """Extract video ID from YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        11-character video ID or None
    """
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def parse_tiktok_url(url: str) -> str | None:
    """Extract video ID from TikTok URL.

    Args:
        url: TikTok URL

    Returns:
        Numeric video ID or short code (for vm.tiktok.com)
    """
    for pattern in TIKTOK_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def parse_sora_url(url: str) -> str | None:
    """Extract video/share ID from Sora/ChatGPT URL.

    Args:
        url: Sora or ChatGPT URL

    Returns:
        Video/share ID or None
    """
    for pattern in SORA_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def detect_platform(url: str) -> Platform:
    """Detect which platform a URL belongs to.

    Args:
        url: Video URL

    Returns:
        Platform enum value
    """
    url_lower = url.lower()

    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return Platform.YOUTUBE
    if "tiktok.com" in url_lower or "vm.tiktok.com" in url_lower:
        return Platform.TIKTOK
    if "sora.com" in url_lower or "chatgpt.com" in url_lower:
        return Platform.SORA

    return Platform.UNKNOWN


def parse_url(url: str) -> ParsedURL:
    """Parse a video URL and extract platform and video ID.

    Args:
        url: Video URL from any supported platform

    Returns:
        ParsedURL with platform, video_id, and validity info

    Examples:
        >>> parse_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        ParsedURL(platform=Platform.YOUTUBE, video_id="dQw4w9WgXcQ", ...)

        >>> parse_url("https://tiktok.com/@user/video/1234567890")
        ParsedURL(platform=Platform.TIKTOK, video_id="1234567890", ...)
    """
    platform = detect_platform(url)

    if platform == Platform.YOUTUBE:
        video_id = parse_youtube_url(url)
        return ParsedURL(
            platform=platform,
            video_id=video_id,
            original_url=url,
            is_valid=video_id is not None,
        )

    if platform == Platform.TIKTOK:
        video_id = parse_tiktok_url(url)
        return ParsedURL(
            platform=platform,
            video_id=video_id,
            original_url=url,
            is_valid=video_id is not None,
        )

    if platform == Platform.SORA:
        video_id = parse_sora_url(url)
        return ParsedURL(
            platform=platform,
            video_id=video_id,
            original_url=url,
            is_valid=video_id is not None,
        )

    return ParsedURL(
        platform=Platform.UNKNOWN,
        video_id=None,
        original_url=url,
        is_valid=False,
    )


def is_supported_url(url: str) -> bool:
    """Check if URL is from a supported platform.

    Args:
        url: URL to check

    Returns:
        True if URL can be processed by aivid
    """
    parsed = parse_url(url)
    return parsed.is_valid
