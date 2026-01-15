"""Base detector class for watermark detection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from aivid.models import VideoMetadata
    from aivid.models.watermark import WatermarkDetection


class BaseDetector(ABC):
    """Abstract base class for watermark detectors.

    Subclasses should implement:
    - is_available(): Check if dependencies are installed
    - detect(): Detect watermarks and return results
    """

    name: ClassVar[str] = "base"
    priority: ClassVar[int] = 100

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this detector is available.

        Returns:
            True if all dependencies are installed
        """
        pass

    @abstractmethod
    def detect(self, path: str, metadata: VideoMetadata) -> WatermarkDetection | None:
        """Detect watermarks in the file.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object (may be used for context)

        Returns:
            WatermarkDetection result or None if no detection attempted
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
