"""AI detection result models."""

from pydantic import BaseModel, Field

# AI Generator mappings
AI_GENERATORS = {
    "Sora": "OpenAI Sora",
    "DALL-E": "OpenAI DALL-E",
    "Midjourney": "Midjourney",
    "Stable Diffusion": "Stability AI",
    "StabilityAI": "Stability AI",
    "Adobe Firefly": "Adobe Firefly",
    "Firefly": "Adobe Firefly",
    "Runway": "Runway ML",
    "Pika": "Pika Labs",
    "Kling": "Kuaishou Kling",
    "Luma": "Luma AI",
    "Gemini": "Google Gemini",
    "Veo": "Google Veo",
}

# Signing authority mappings
SIGNING_AUTHORITIES = ["OpenAI", "Adobe", "Microsoft", "Google", "Meta", "Apple"]

# Sora model resolution mappings (based on OpenAI API pricing)
# sora-2: 720x1280 only ($0.10/s)
# sora-2-pro: 720x1280 ($0.30/s) or 1024x1792 ($0.50/s)
SORA_PRO_EXCLUSIVE_RESOLUTIONS = [
    (1024, 1792),  # Portrait
    (1792, 1024),  # Landscape
]
SORA_SHARED_RESOLUTIONS = [
    (720, 1280),  # Portrait API standard
    (1280, 720),  # Landscape API standard
    (704, 1280),  # Portrait - Sora web download (compressed)
    (1280, 704),  # Landscape - Sora web download (compressed)
]


def infer_sora_model(width: int, height: int) -> tuple[str | None, str]:
    """Infer Sora model based on video resolution.

    Args:
        width: Video width in pixels
        height: Video height in pixels

    Returns:
        Tuple of (model_name, confidence):
        - model_name: "sora-2-pro" if confirmed, None otherwise
        - confidence: "confirmed" | "ambiguous" | "unknown"

    Note:
        Sora web downloads may have slightly different resolutions (e.g., 704x1280)
        compared to API outputs (720x1280) due to compression.
    """
    resolution = (width, height)

    if resolution in SORA_PRO_EXCLUSIVE_RESOLUTIONS:
        return ("sora-2-pro", "confirmed")
    elif resolution in SORA_SHARED_RESOLUTIONS:
        return (None, "ambiguous")  # Could be sora-2 or sora-2-pro
    else:
        return (None, "unknown")


class AISignal(BaseModel):
    """A single AI detection signal.

    Signals can be either:
    - FACT: Directly extracted from metadata (e.g., C2PA digitalSourceType)
    - ANALYSIS: Inferred from patterns or heuristics (e.g., 96kHz audio)
    """

    name: str
    detected: bool = False
    confidence: float = 0.0  # 0-1
    description: str | None = None
    is_fact: bool = False  # True = direct metadata, False = analysis/inference


class AIDetectionResult(BaseModel):
    """AI content detection results."""

    is_ai_generated: bool = False
    generator: str | None = None  # Normalized: "OpenAI Sora", "Google Veo"
    generator_raw: str | None = None  # Raw claim generator value
    confidence: float = 0.0  # Overall confidence 0-1

    # Model inference (for generators with multiple models)
    inferred_model: str | None = None  # e.g., "sora-2-pro"
    model_confidence: str | None = None  # "confirmed", "ambiguous", "unknown"

    # Detection signals
    signals: dict[str, AISignal] = Field(default_factory=dict)

    # Signing info
    signing_authorities: list[str] = Field(default_factory=list)

    @classmethod
    def from_c2pa(
        cls,
        claim_generator: str | None,
        digital_source_type: str | None,
        issuer: str | None,
        audio_sample_rate: int | None = None,
        video_width: int | None = None,
        video_height: int | None = None,
    ) -> "AIDetectionResult":
        """Create detection result from C2PA info."""
        result = cls()

        # Detect AI generation from digital source type
        if digital_source_type and "trainedAlgorithmicMedia" in digital_source_type:
            result.is_ai_generated = True
            result.confidence = 1.0
            result.signals["c2pa_source_type"] = AISignal(
                name="C2PA Digital Source Type",
                detected=True,
                confidence=1.0,
                description=f"digitalSourceType: {digital_source_type}",
                is_fact=True,  # Direct C2PA metadata
            )

        # Identify generator
        if claim_generator:
            result.generator_raw = claim_generator
            for key, value in AI_GENERATORS.items():
                if key.lower() in claim_generator.lower():
                    result.generator = value
                    result.is_ai_generated = True
                    break

        # Detect signing authority
        if issuer:
            for auth in SIGNING_AUTHORITIES:
                if auth.lower() in issuer.lower():
                    result.signing_authorities.append(auth)

        # Check 96kHz audio (Sora signature) - this is analysis, not direct AI declaration
        if audio_sample_rate == 96000:
            result.signals["audio_96khz"] = AISignal(
                name="96kHz Audio",
                detected=True,
                confidence=0.9,
                description="96kHz audio sample rate (Sora signature)",
                is_fact=False,  # Analysis: 96kHz is unusual and suggests Sora
            )
            if not result.generator:
                result.generator = "OpenAI Sora"
                result.is_ai_generated = True
                result.confidence = max(result.confidence, 0.9)

        # Infer Sora model from resolution (only if generator is Sora)
        if result.generator == "OpenAI Sora" and video_width and video_height:
            model, confidence = infer_sora_model(video_width, video_height)
            result.inferred_model = model
            result.model_confidence = confidence

        return result

    def add_signal(
        self,
        name: str,
        detected: bool,
        confidence: float = 0.0,
        description: str | None = None,
        is_fact: bool = False,
    ) -> None:
        """Add a detection signal.

        Args:
            name: Signal identifier
            detected: Whether the signal was detected
            confidence: Detection confidence (0-1)
            description: Human-readable description
            is_fact: True if directly from metadata, False if inferred/analyzed
        """
        self.signals[name] = AISignal(
            name=name,
            detected=detected,
            confidence=confidence,
            description=description,
            is_fact=is_fact,
        )
        if detected and confidence > self.confidence:
            self.confidence = confidence
