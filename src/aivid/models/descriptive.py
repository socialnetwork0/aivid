"""Descriptive metadata models (XMP, EXIF, IPTC)."""

from datetime import datetime

from pydantic import BaseModel, Field


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
