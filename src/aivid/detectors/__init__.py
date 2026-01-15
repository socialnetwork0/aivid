"""Watermark detectors for AI-generated content.

Supported detectors:
- AudioSeal: Meta's audio watermark detector (pip install audioseal)
- VideoSeal: Meta's video watermark detector (from GitHub)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseDetector

if TYPE_CHECKING:
    from aivid.models import VideoMetadata


def get_available_detectors() -> list[BaseDetector]:
    """Get list of available detector instances.

    Returns:
        List of detector instances that are available on this system.
    """
    available: list[BaseDetector] = []

    try:
        from .audioseal import AudioSealDetector

        if AudioSealDetector.is_available():
            available.append(AudioSealDetector())
    except ImportError:
        pass

    try:
        from .videoseal import VideoSealDetector

        if VideoSealDetector.is_available():
            available.append(VideoSealDetector())
    except ImportError:
        pass

    return available


def run_watermark_detection(path: str, metadata: VideoMetadata) -> None:
    """Run all available watermark detectors on a file.

    Args:
        path: Path to the video file
        metadata: VideoMetadata object to populate with results
    """
    detectors = get_available_detectors()

    for detector in detectors:
        try:
            result = detector.detect(path, metadata)
            if result:
                metadata.provenance.watermarks.add_detection(result)
        except Exception:
            # Graceful degradation - detector errors don't fail the analysis
            pass


def get_detector_status() -> dict[str, bool]:
    """Get availability status of all detectors.

    Returns:
        Dict mapping detector names to availability status.
    """
    status = {}

    try:
        from .audioseal import AudioSealDetector

        status["audioseal"] = AudioSealDetector.is_available()
    except ImportError:
        status["audioseal"] = False

    try:
        from .videoseal import VideoSealDetector

        status["videoseal"] = VideoSealDetector.is_available()
    except ImportError:
        status["videoseal"] = False

    return status


__all__ = [
    "BaseDetector",
    "get_available_detectors",
    "run_watermark_detection",
    "get_detector_status",
]
