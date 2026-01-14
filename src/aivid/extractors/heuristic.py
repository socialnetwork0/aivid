"""Heuristic AI detection based on audio/video characteristics."""

from typing import ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import VideoMetadata


class HeuristicDetector(BaseExtractor):
    """Detect AI-generated content using heuristic signals.

    This extractor analyzes audio/video characteristics that are
    commonly found in AI-generated content:

    - 96kHz audio sample rate (Sora signature)
    - Specific encoder tags (Google/Gemini/Veo)
    - Handler name patterns

    This runs after other extractors to analyze their results.
    """

    name: ClassVar[str] = "heuristic"
    priority: ClassVar[int] = 90  # Run late, after technical extraction

    @classmethod
    def is_available(cls) -> bool:
        """Always available."""
        return True

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Detect AI signals from extracted metadata."""
        ai = metadata.ai_detection
        tech = metadata.technical

        # Check 96kHz audio (Sora signature)
        if tech.audio.sample_rate == 96000:
            ai.add_signal(
                "audio_96khz",
                True,
                0.9,
                "96kHz audio sample rate (Sora signature)",
            )
            if not ai.generator:
                ai.generator = "OpenAI Sora"
            ai.is_ai_generated = True

        # Check encoder tags
        encoder = tech.video.encoder or ""
        if "Google" in encoder:
            ai.add_signal(
                "encoder_google",
                True,
                0.8,
                f"Google encoder detected: {encoder}",
            )
            if not ai.generator:
                ai.generator = "Google Veo"
            ai.is_ai_generated = True

        # Check handler name
        handler = tech.video.handler or ""
        if "Google" in handler:
            ai.add_signal(
                "handler_google",
                True,
                0.7,
                f"Google handler detected: {handler}",
            )
        if "Mainconcept" in handler:
            ai.add_signal(
                "handler_mainconcept",
                True,
                0.6,
                f"Mainconcept handler (possible Luma): {handler}",
            )

        # Check format tags for encoder info
        format_tags = metadata.raw.format_tags
        format_encoder = format_tags.get("encoder", "")
        if format_encoder == "Google":
            ai.add_signal(
                "format_encoder_google",
                True,
                0.85,
                "Format encoder tag: Google",
            )
            if not ai.generator:
                ai.generator = "Google Gemini/Veo"
            ai.is_ai_generated = True

        # Calculate overall confidence
        if ai.signals:
            detected_signals = [s for s in ai.signals.values() if s.detected]
            if detected_signals:
                # Use highest signal confidence
                ai.confidence = max(s.confidence for s in detected_signals)
