"""Descriptive metadata models (XMP, EXIF, IPTC)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TimestampInfo(BaseModel):
    """Timestamp with source attribution.

    Tracks where the timestamp came from for transparency and priority handling.
    """

    value: datetime | None = None
    source: Literal["c2pa", "exiftool", "ffprobe", "filesystem"] | None = None
    raw_value: str | None = None  # Original string before parsing


class IPTCAIInfo(BaseModel):
    """IPTC 2025.1 AI-related metadata fields.

    Supports the new AI Content Declaration fields from IPTC Photo Metadata
    Standard 2025.1 for marking AI-generated content.
    """

    ai_system_used: str | None = None  # AISystemUsed - e.g., "OpenAI DALL-E 3"
    ai_system_version: str | None = None  # AISystemVersion
    ai_prompt_info: str | None = None  # AIPromptInfo - the prompt used
    ai_prompt_writer_name: str | None = None  # AIPromptWriterName
    ai_generated: bool | None = None  # AIGenerated flag
    ai_training_mining_usage: str | None = None  # AITrainingMiningUsage


class DescriptiveMetadata(BaseModel):
    """Descriptive metadata from XMP, EXIF, IPTC standards."""

    # Basic info
    title: str | None = None
    description: str | None = None
    creator: str | None = None
    publisher: str | None = None
    copyright: str | None = None

    # Creation info
    creation_date: datetime | None = None
    modification_date: datetime | None = None
    software: str | None = None  # Creating software

    # Detailed timestamp tracking with source attribution
    creation_timestamp: TimestampInfo = Field(default_factory=TimestampInfo)
    modification_timestamp: TimestampInfo = Field(default_factory=TimestampInfo)

    # IPTC 2025.1 AI metadata fields
    iptc_ai: IPTCAIInfo = Field(default_factory=IPTCAIInfo)

    # Keywords and categorization
    keywords: list[str] = Field(default_factory=list)
    genre: str | None = None
    rating: int | None = None  # 0-5 stars

    # Location (from EXIF GPS)
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    gps_altitude: float | None = None
    location_name: str | None = None

    # Device info (from EXIF)
    camera_make: str | None = None
    camera_model: str | None = None

    @property
    def has_gps(self) -> bool:
        """Check if GPS coordinates are available."""
        return self.gps_latitude is not None and self.gps_longitude is not None

    @property
    def gps_coordinates(self) -> str | None:
        """Return GPS coordinates as string."""
        if not self.has_gps:
            return None
        return f"{self.gps_latitude:.6f}, {self.gps_longitude:.6f}"
