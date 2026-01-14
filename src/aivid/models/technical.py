"""Technical metadata models for video files."""

from typing import Any

from pydantic import BaseModel, Field


class VideoStream(BaseModel):
    """Video stream technical information."""

    codec: str | None = None
    codec_long: str | None = None
    profile: str | None = None
    level: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    avg_fps: float | None = None
    bitrate: int | None = None
    duration: float | None = None
    pixel_format: str | None = None
    color_space: str | None = None
    field_order: str | None = None
    encoder: str | None = None
    handler: str | None = None

    @property
    def resolution(self) -> str | None:
        """Return resolution as WxH string."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    @property
    def aspect_ratio(self) -> str | None:
        """Calculate aspect ratio from width and height."""
        if not self.width or not self.height:
            return None
        from math import gcd

        divisor = gcd(self.width, self.height)
        w_ratio = self.width // divisor
        h_ratio = self.height // divisor
        # Simplify common ratios
        common_ratios = {
            (16, 9): "16:9",
            (9, 16): "9:16",
            (4, 3): "4:3",
            (3, 4): "3:4",
            (21, 9): "21:9",
            (1, 1): "1:1",
            (3, 2): "3:2",
            (2, 3): "2:3",
        }
        return common_ratios.get((w_ratio, h_ratio), f"{w_ratio}:{h_ratio}")


class AudioStream(BaseModel):
    """Audio stream technical information."""

    codec: str | None = None
    codec_long: str | None = None
    profile: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None
    bitrate: int | None = None
    duration: float | None = None
    sample_format: str | None = None
    handler: str | None = None


class TechnicalMetadata(BaseModel):
    """Technical metadata for video files."""

    container: str | None = None
    container_long: str | None = None
    duration: float | None = None
    bitrate: int | None = None
    size_bytes: int | None = None
    nb_streams: int | None = None
    video: VideoStream = Field(default_factory=VideoStream)
    audio: AudioStream = Field(default_factory=AudioStream)
    # Additional streams (subtitles, data, etc.)
    other_streams: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def duration_formatted(self) -> str:
        """Return duration as human-readable string."""
        if not self.duration:
            return "N/A"
        duration = self.duration
        if duration < 60:
            return f"{duration:.1f}s"
        minutes = int(duration // 60)
        seconds = duration % 60
        if minutes < 60:
            return f"{minutes}m {seconds:.1f}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {seconds:.0f}s"
