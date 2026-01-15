"""Heuristic AI detection based on audio/video characteristics."""

from typing import ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import VideoMetadata

# Platform encoder tags that should NOT trigger AI detection
# These are added by video platforms during transcoding, not by AI generators
PLATFORM_ENCODER_PATTERNS = [
    "ISO Media file produced by Google Inc.",  # YouTube transcoding
    "Lavf",  # FFmpeg (common in many platforms)
]


class HeuristicDetector(BaseExtractor):
    """Detect AI-generated content using heuristic signals.

    This extractor analyzes audio/video characteristics that are
    commonly found in AI-generated content:

    - 96kHz audio sample rate (Sora signature)
    - Specific encoder tags (NOT platform transcoding tags)
    - Handler name patterns

    IMPORTANT: Platform transcoding tags (like YouTube's "Google" encoder)
    should NOT trigger AI detection. Only AI-specific signatures should.

    This runs after other extractors to analyze their results.
    """

    name: ClassVar[str] = "heuristic"
    priority: ClassVar[int] = 90  # Run late, after technical extraction

    @classmethod
    def is_available(cls) -> bool:
        """Always available."""
        return True

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Detect AI signals from extracted metadata.

        All signals from this detector are ANALYSIS (is_fact=False)
        because they are inferred from patterns, not direct AI declarations.
        """
        ai = metadata.ai_detection
        tech = metadata.technical

        # Check if this looks like a platform-transcoded video
        handler = tech.video.handler or ""
        format_tags = metadata.raw.format_tags
        format_encoder = format_tags.get("encoder", "")

        is_platform_video = self._is_platform_transcoded(handler, format_encoder)

        # Check 96kHz audio (Sora signature) - ANALYSIS: unusual rate suggests Sora
        # This is a strong signal that applies regardless of platform
        if tech.audio.sample_rate == 96000:
            ai.add_signal(
                "audio_96khz",
                True,
                0.9,
                "96kHz audio sample rate (Sora signature)",
                is_fact=False,  # Analysis: inferred from unusual sample rate
            )
            if not ai.generator:
                ai.generator = "OpenAI Sora"
            ai.is_ai_generated = True

        # Only check encoder/handler tags if NOT a platform-transcoded video
        # Platform videos (YouTube, etc.) have Google tags from transcoding, not AI
        if not is_platform_video:
            encoder = tech.video.encoder or ""
            if "Google" in encoder and "Veo" in encoder:
                # Only trigger if explicitly mentions Veo
                ai.add_signal(
                    "encoder_google_veo",
                    True,
                    0.8,
                    f"Google Veo encoder detected: {encoder}",
                    is_fact=False,
                )
                if not ai.generator:
                    ai.generator = "Google Veo"
                ai.is_ai_generated = True

            # Mainconcept handler (possible Luma)
            if "Mainconcept" in handler:
                ai.add_signal(
                    "handler_mainconcept",
                    True,
                    0.6,
                    f"Mainconcept handler (possible Luma): {handler}",
                    is_fact=False,  # Analysis: weak signal, may indicate Luma
                )

        # Calculate overall confidence
        if ai.signals:
            detected_signals = [s for s in ai.signals.values() if s.detected]
            if detected_signals:
                # Use highest signal confidence
                ai.confidence = max(s.confidence for s in detected_signals)

    def _is_platform_transcoded(self, handler: str, format_encoder: str) -> bool:
        """Check if video appears to be transcoded by a platform (YouTube, etc.).

        Platform transcoding adds encoder tags that should NOT trigger AI detection.

        Args:
            handler: Video handler string
            format_encoder: Format encoder tag

        Returns:
            True if video appears to be platform-transcoded
        """
        # Check for known platform patterns
        for pattern in PLATFORM_ENCODER_PATTERNS:
            if pattern in handler:
                return True

        # YouTube/Google platform transcoding
        # "ISO Media file produced by Google Inc." is YouTube's transcoder
        if "ISO Media file produced by Google" in handler:
            return True

        # Format encoder "Google" alone (without Veo) is just platform encoding
        if format_encoder == "Google" and "Veo" not in handler:
            return True

        return False
