"""Base extractor class."""

from abc import ABC, abstractmethod
from typing import ClassVar

from aivid.models import VideoMetadata


class BaseExtractor(ABC):
    """Abstract base class for metadata extractors.

    Extractors are responsible for extracting specific types of metadata
    from video files. They follow a plugin architecture where each extractor
    can check its own availability and gracefully skip if dependencies
    are not available.

    Attributes:
        name: Human-readable name of the extractor
        priority: Lower numbers run first (default: 100)
    """

    name: ClassVar[str] = "base"
    priority: ClassVar[int] = 100

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this extractor is available.

        Returns:
            True if all dependencies are available
        """
        pass

    @abstractmethod
    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Extract metadata and populate the VideoMetadata object.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object to populate (modified in place)
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, priority={self.priority})"
