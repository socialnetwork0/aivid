"""Watermark detection models.

Models for storing watermark detection results from various detectors:
- AudioSeal: Meta's audio watermark detector
- VideoSeal: Meta's video watermark detector
- SynthID: Google's watermark (reserved, detection not publicly available)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WatermarkDetection(BaseModel):
    """Individual watermark detection result.

    Attributes:
        detector: Name of the detector (e.g., "audioseal", "videoseal")
        detected: Whether a watermark was detected
        confidence: Detection confidence (0-1)
        watermark_type: Type of watermark (audio, video, image)
        message_bits: Number of bits in the watermark message
        message_decoded: Decoded message (if available)
        frames_analyzed: Number of frames analyzed (for video)
        positive_frames: Number of frames with watermark detected
        detection_threshold: Threshold used for detection
    """

    detector: str
    detected: bool = False
    confidence: float = 0.0
    watermark_type: str | None = None  # "audio", "video", "image"

    # Watermark-specific fields
    message_bits: int | None = None  # For AudioSeal: 16-bit message
    message_decoded: str | None = None

    # Detection details
    frames_analyzed: int | None = None
    positive_frames: int | None = None
    detection_threshold: float | None = None

    @property
    def is_high_confidence(self) -> bool:
        """Check if detection is high confidence (>0.8)."""
        return self.detected and self.confidence > 0.8


class WatermarkResults(BaseModel):
    """Aggregated watermark detection results.

    Combines results from multiple watermark detectors into a single
    result object with overall detection status.
    """

    has_watermark: bool = False
    detections: list[WatermarkDetection] = Field(default_factory=list)

    # Aggregated confidence
    overall_confidence: float = 0.0

    def add_detection(self, detection: WatermarkDetection) -> None:
        """Add a watermark detection result.

        Updates has_watermark and overall_confidence based on the new detection.

        Args:
            detection: WatermarkDetection result to add
        """
        self.detections.append(detection)
        if detection.detected:
            self.has_watermark = True
            self.overall_confidence = max(self.overall_confidence, detection.confidence)

    @property
    def audio_watermark(self) -> WatermarkDetection | None:
        """Get audio watermark detection result if any."""
        for d in self.detections:
            if d.watermark_type == "audio":
                return d
        return None

    @property
    def video_watermark(self) -> WatermarkDetection | None:
        """Get video watermark detection result if any."""
        for d in self.detections:
            if d.watermark_type == "video":
                return d
        return None

    @property
    def detection_summary(self) -> str:
        """Get a summary of detection results."""
        if not self.detections:
            return "No watermark detection performed"

        if not self.has_watermark:
            return "No watermarks detected"

        detected = [d for d in self.detections if d.detected]
        parts = []
        for d in detected:
            parts.append(f"{d.detector}: {d.confidence:.1%}")
        return ", ".join(parts)
