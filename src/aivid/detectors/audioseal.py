"""AudioSeal watermark detector from Meta.

AudioSeal detects 16-bit watermarks embedded in audio by AI generators.
It provides localized detection at the sample level (1/16,000 of a second).

Requirements:
- audioseal: pip install audioseal
- torch: pip install torch
- torchaudio: pip install torchaudio
- ffmpeg: for audio extraction

Reference: https://github.com/facebookresearch/audioseal
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile
from typing import TYPE_CHECKING, ClassVar

from aivid.config import get_config
from aivid.models.watermark import WatermarkDetection

from .base import BaseDetector

if TYPE_CHECKING:
    from aivid.models import VideoMetadata


class AudioSealDetector(BaseDetector):
    """Detect Meta AudioSeal watermarks in audio tracks.

    AudioSeal can:
    1. Detect presence of watermark (probability 0-1)
    2. Decode 16-bit message embedded in watermark

    Note: This detector extracts the audio track from video files
    using FFmpeg before running detection.
    """

    name: ClassVar[str] = "audioseal"
    priority: ClassVar[int] = 80

    @classmethod
    def is_available(cls) -> bool:
        """Check if audioseal and dependencies are available."""
        try:
            import audioseal  # noqa: F401
            import torch  # noqa: F401
            import torchaudio  # noqa: F401

            return True
        except ImportError:
            return False

    def detect(self, path: str, metadata: VideoMetadata) -> WatermarkDetection | None:
        """Detect AudioSeal watermarks in audio track.

        Args:
            path: Path to the video file
            metadata: VideoMetadata object

        Returns:
            WatermarkDetection result or None if detection fails
        """
        # Check if video has audio
        if metadata.technical.audio.codec is None:
            return None

        # Extract audio track
        audio_path = self._extract_audio(path)
        if not audio_path:
            return None

        try:
            import torch
            import torchaudio
            from audioseal import AudioSeal

            # Load detector model
            detector = AudioSeal.load_detector("audioseal_detector_16bits")

            # Load audio
            waveform, sample_rate = torchaudio.load(audio_path)

            # Resample to 16kHz if needed (AudioSeal works best at 16kHz)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)

            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            # Add batch dimension
            waveform = waveform.unsqueeze(0)

            # Detect watermark
            config = get_config()
            threshold = config.detection.audioseal_threshold

            with torch.no_grad():
                result, message = detector.detect_watermark(waveform)

                # result is a tensor with detection probability
                confidence = float(result.mean())
                detected = confidence > threshold

                detection = WatermarkDetection(
                    detector="audioseal",
                    detected=detected,
                    confidence=confidence,
                    watermark_type="audio",
                    message_bits=16,
                    message_decoded=self._decode_message(message) if detected else None,
                    detection_threshold=threshold,
                )

                return detection

        except Exception:
            return None
        finally:
            # Cleanup temp audio file
            if audio_path and os.path.exists(audio_path):
                with contextlib.suppress(OSError):
                    os.unlink(audio_path)

    def _extract_audio(self, video_path: str) -> str | None:
        """Extract audio track from video using FFmpeg.

        Args:
            video_path: Path to the video file

        Returns:
            Path to extracted WAV file or None if extraction fails
        """
        try:
            # Create temp file for audio
            fd, audio_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

            # Extract audio with FFmpeg
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    video_path,
                    "-vn",  # No video
                    "-acodec",
                    "pcm_s16le",  # 16-bit PCM
                    "-ar",
                    "16000",  # 16kHz sample rate
                    "-ac",
                    "1",  # Mono
                    "-y",  # Overwrite
                    audio_path,
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0 and os.path.exists(audio_path):
                return audio_path

            # Cleanup on failure
            if os.path.exists(audio_path):
                os.unlink(audio_path)
            return None

        except Exception:
            return None

    @staticmethod
    def _decode_message(message) -> str:
        """Decode 16-bit message from watermark tensor.

        Args:
            message: Tensor of shape (batch, bits)

        Returns:
            Binary string representation of the message
        """
        try:
            # message is typically shape (1, 16) for 16-bit watermark
            bits = (message > 0.5).int().squeeze().tolist()
            if isinstance(bits, int):
                return str(bits)
            return "".join(str(b) for b in bits)
        except Exception:
            return ""
