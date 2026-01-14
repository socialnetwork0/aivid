"""Main VideoMetadata model."""

from pydantic import BaseModel, ConfigDict, Field

from .ai import AIDetectionResult
from .descriptive import DescriptiveMetadata
from .file import FileInfo
from .provenance import ProvenanceMetadata
from .raw import RawMetadata
from .technical import TechnicalMetadata


class VideoMetadata(BaseModel):
    """Unified video metadata model.

    This is the main model returned by aivid's extraction functions.
    It organizes metadata into logical categories:

    - file_info: Basic file information (path, size, timestamps)
    - technical: Video/audio technical specs (codec, resolution, bitrate)
    - descriptive: XMP/EXIF/IPTC metadata (title, creator, keywords)
    - provenance: C2PA content credentials
    - ai_detection: AI generation detection results
    - raw: Raw data from extraction tools (for debugging)
    """

    file_info: FileInfo
    technical: TechnicalMetadata = Field(default_factory=TechnicalMetadata)
    descriptive: DescriptiveMetadata = Field(default_factory=DescriptiveMetadata)
    provenance: ProvenanceMetadata = Field(default_factory=ProvenanceMetadata)
    ai_detection: AIDetectionResult = Field(default_factory=AIDetectionResult)
    raw: RawMetadata = Field(default_factory=RawMetadata)

    # Convenience properties
    @property
    def path(self) -> str:
        """Return file path."""
        return self.file_info.path

    @property
    def filename(self) -> str:
        """Return filename."""
        return self.file_info.filename

    @property
    def is_ai_generated(self) -> bool:
        """Check if video is detected as AI-generated."""
        return self.ai_detection.is_ai_generated or self.provenance.c2pa.is_ai_generated

    @property
    def ai_generator(self) -> str | None:
        """Return AI generator name if detected."""
        return self.ai_detection.generator

    @property
    def has_c2pa(self) -> bool:
        """Check if C2PA metadata is present."""
        return self.provenance.c2pa.has_c2pa

    @property
    def duration(self) -> float | None:
        """Return video duration in seconds."""
        return self.technical.duration

    @property
    def resolution(self) -> str | None:
        """Return video resolution as WxH."""
        return self.technical.video.resolution

    model_config = ConfigDict(arbitrary_types_allowed=True)
