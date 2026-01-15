"""VideoSeal watermark detector from Meta.

VideoSeal detects watermarks embedded in video frames using temporal
watermark propagation for efficient detection.

Requirements:
- videoseal: Install from https://github.com/facebookresearch/videoseal
- torch: pip install torch
- torchvision: pip install torchvision
- Python 3.10+

Reference: https://github.com/facebookresearch/videoseal
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from aivid.config import get_config
from aivid.models.watermark import WatermarkDetection

from .base import BaseDetector

if TYPE_CHECKING:
    from aivid.models import VideoMetadata


class VideoSealDetector(BaseDetector):
    """Detect Meta VideoSeal watermarks in video frames.

    VideoSeal provides:
    1. Efficient video watermark detection with temporal consistency
    2. Support for 256-bit watermarks
    3. Robustness against H.264, HEVC, and AV1 encoding

    Note: VideoSeal is computationally intensive. Consider sampling
    frames for longer videos.
    """

    name: ClassVar[str] = "videoseal"
    priority: ClassVar[int] = 81

    # Maximum frames to analyze (for performance)
    MAX_FRAMES = 30

    @classmethod
    def is_available(cls) -> bool:
        """Check if videoseal and dependencies are available."""
        try:
            # VideoSeal may not be on PyPI, check for the module
            import torch  # noqa: F401
            import torchvision  # noqa: F401

            # Try to import videoseal
            try:
                import videoseal  # noqa: F401

                return True
            except ImportError:
                return False

        except ImportError:
            return False

    def detect(self, path: str, metadata: VideoMetadata) -> WatermarkDetection | None:
        """Detect VideoSeal watermarks in video frames.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object

        Returns:
            WatermarkDetection result or None if detection fails
        """
        try:
            import torch
            from torchvision.io import read_video

            # Load video frames
            video, audio, info = read_video(path, pts_unit="sec")

            if video.shape[0] == 0:
                return None

            # Sample frames if video is too long
            num_frames = video.shape[0]
            if num_frames > self.MAX_FRAMES:
                indices = torch.linspace(0, num_frames - 1, self.MAX_FRAMES).long()
                video = video[indices]
                num_frames = self.MAX_FRAMES

            # Normalize frames to [0, 1]
            video = video.float() / 255.0

            # Load VideoSeal detector
            try:
                import videoseal

                detector = videoseal.load_detector()
            except Exception:
                return None

            # Run detection on frames
            config = get_config()
            threshold = config.detection.videoseal_threshold

            with torch.no_grad():
                # VideoSeal expects (B, C, H, W) format
                # video is (T, H, W, C), convert to (T, C, H, W)
                video = video.permute(0, 3, 1, 2)

                positive_frames = 0
                total_confidence = 0.0

                for frame in video:
                    frame = frame.unsqueeze(0)  # Add batch dim
                    result = detector(frame)

                    if hasattr(result, "item"):
                        conf = float(result.item())
                    else:
                        conf = float(result)

                    total_confidence += conf
                    if conf > threshold:
                        positive_frames += 1

                avg_confidence = total_confidence / num_frames
                detected = avg_confidence > threshold

                detection = WatermarkDetection(
                    detector="videoseal",
                    detected=detected,
                    confidence=avg_confidence,
                    watermark_type="video",
                    frames_analyzed=num_frames,
                    positive_frames=positive_frames,
                    detection_threshold=threshold,
                )

                return detection

        except Exception:
            return None
