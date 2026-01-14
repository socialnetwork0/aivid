"""Data models for aivid."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetadataReport:
    """Complete metadata report for a media file."""

    file_path: str = ""
    file_info: dict[str, Any] = field(default_factory=dict)
    container_info: dict[str, Any] = field(default_factory=dict)
    box_structure: list[dict[str, Any]] = field(default_factory=list)
    streams: list[dict[str, Any]] = field(default_factory=list)
    stream_details: list[dict[str, Any]] = field(default_factory=list)
    format_tags: dict[str, Any] = field(default_factory=dict)
    c2pa_info: dict[str, Any] = field(default_factory=dict)
    xmp_metadata: dict[str, Any] = field(default_factory=dict)
    creation_info: dict[str, Any] = field(default_factory=dict)
    encoding_info: dict[str, Any] = field(default_factory=dict)
    gps_info: dict[str, Any] = field(default_factory=dict)
    custom_tags: dict[str, Any] = field(default_factory=dict)
    raw_strings: list[str] = field(default_factory=list)
    chapters: list[dict[str, Any]] = field(default_factory=list)
    programs: list[dict[str, Any]] = field(default_factory=list)
    ffprobe_raw: dict[str, Any] = field(default_factory=dict)
    mediainfo_raw: dict[str, Any] = field(default_factory=dict)
    exiftool_raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ai_generated(self) -> bool:
        """Check if the file appears to be AI-generated based on C2PA info."""
        result = self.c2pa_info.get("has_c2pa", False)
        return bool(result)

    @property
    def ai_generator(self) -> str | None:
        """Get the AI generator name if detected."""
        result = self.c2pa_info.get("generator")
        if result is None:
            return None
        return str(result)
