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


class AISignal(BaseModel):
    """A single AI detection signal."""

    name: str
    detected: bool = False
    confidence: float = 0.0  # 0-1
    description: str | None = None


class AIDetectionResult(BaseModel):
    """AI content detection results."""

    is_ai_generated: bool = False
    generator: str | None = None  # Normalized: "OpenAI Sora", "Google Veo"
    generator_raw: str | None = None  # Raw claim generator value
    confidence: float = 0.0  # Overall confidence 0-1

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

        # Check 96kHz audio (Sora signature)
        if audio_sample_rate == 96000:
            result.signals["audio_96khz"] = AISignal(
                name="96kHz Audio",
                detected=True,
                confidence=0.9,
                description="96kHz audio sample rate (Sora signature)",
            )
            if not result.generator:
                result.generator = "OpenAI Sora"
                result.is_ai_generated = True
                result.confidence = max(result.confidence, 0.9)

        return result

    def add_signal(
        self,
        name: str,
        detected: bool,
        confidence: float = 0.0,
        description: str | None = None,
    ) -> None:
        """Add a detection signal."""
        self.signals[name] = AISignal(
            name=name, detected=detected, confidence=confidence, description=description
        )
        if detected and confidence > self.confidence:
            self.confidence = confidence
