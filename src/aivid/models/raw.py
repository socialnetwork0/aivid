"""Raw metadata storage models."""

from typing import Any

from pydantic import BaseModel, Field


class BoxInfo(BaseModel):
    """MP4/MOV box structure information."""

    type: str
    size: int
    offset: int
    depth: int = 0
    data_preview: str | None = None


class RawMetadata(BaseModel):
    """Raw metadata from various extraction tools."""

    # FFprobe raw output
    ffprobe: dict[str, Any] | None = None

    # MediaInfo raw output
    mediainfo: dict[str, Any] | None = None

    # ExifTool raw output
    exiftool: dict[str, Any] | None = None

    # C2PA raw manifest
    c2pa: dict[str, Any] | None = None

    # MP4/MOV box structure
    box_structure: list[BoxInfo] = Field(default_factory=list)

    # Interesting strings extracted from binary
    strings: list[str] = Field(default_factory=list)

    # Format tags (from container)
    format_tags: dict[str, Any] = Field(default_factory=dict)

    # Stream details
    streams: list[dict[str, Any]] = Field(default_factory=list)

    # Chapters
    chapters: list[dict[str, Any]] = Field(default_factory=list)

    # Programs (for transport streams)
    programs: list[dict[str, Any]] = Field(default_factory=list)
