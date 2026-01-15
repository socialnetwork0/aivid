"""Provenance metadata models (C2PA)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .watermark import WatermarkResults


class C2PAAction(BaseModel):
    """A single C2PA action from the manifest."""

    action: str  # e.g., "c2pa.created", "c2pa.edited"
    software_agent: str | None = None
    digital_source_type: str | None = None
    when: datetime | None = None


class C2PAInfo(BaseModel):
    """C2PA Content Credentials information."""

    has_c2pa: bool = False
    source: str | None = None  # "c2pa-python", "c2patool", "string"

    # Manifest info
    manifest_id: str | None = None
    title: str | None = None
    format: str | None = None

    # Task/Instance identification (for database indexing and deduplication)
    task_id: str | None = None  # Extracted from title (e.g., "b1f75fc641144ddba74f8392297bc898")
    instance_id: str | None = None  # XMP instance ID (xmp:iid:...)

    # Generator info
    claim_generator: str | None = None
    software_agent: str | None = None

    # Signature info
    issuer: str | None = None
    signer_name: str | None = None
    cert_serial_number: str | None = None
    signature_time: datetime | None = None
    signature_algorithm: str | None = None  # e.g., "es256", "ps256"
    cert_trusted: bool | None = None  # Certificate in default trust list

    # SDK/Tool version tracking
    claim_generator_version: str | None = None  # e.g., "0.67.1"
    claim_generator_product: str | None = None  # e.g., "c2pa-rs"

    # AI-specific
    digital_source_type: str | None = None
    generation_mode: str | None = None  # Inferred: "text2video", "image2video", etc.

    # Actions
    actions: list[C2PAAction] = Field(default_factory=list)

    # Ingredients (for edited content)
    ingredient_count: int = 0
    ingredients: list[dict[str, Any]] = Field(default_factory=list)

    # Validation
    validation_state: str | None = None  # "Valid", "Invalid", etc.
    validation_errors: list[str] = Field(default_factory=list)

    # Validation details (for security auditing)
    timestamp_validated: bool | None = None
    timestamp_responder: str | None = None  # TSA responder name
    claim_signature_valid: bool | None = None
    cert_chain: str | None = None  # e.g., "OpenAI → Truepic → DigiCert"

    # Raw data for debugging
    raw_manifest: dict[str, Any] | None = None

    @property
    def is_ai_generated(self) -> bool:
        """Check if content is marked as AI-generated via C2PA."""
        if self.digital_source_type:
            return "trainedAlgorithmicMedia" in self.digital_source_type
        return False

    @property
    def signing_authority(self) -> str | None:
        """Return the signing authority (issuer)."""
        return self.issuer


class TSATimestamp(BaseModel):
    """RFC 3161 Timestamp Authority verification result.

    Provides cryptographic proof that content existed at a specific time,
    verified by a trusted third-party Timestamp Authority.

    Reserved for future implementation.
    """

    verified: bool = False
    timestamp: datetime | None = None
    tsa_name: str | None = None
    tsa_url: str | None = None
    policy_oid: str | None = None
    hash_algorithm: str | None = None
    message_digest: str | None = None


class SynthIDResult(BaseModel):
    """Google SynthID watermark detection result.

    SynthID embeds invisible watermarks in AI-generated content
    that survive common transformations (cropping, compression, etc.).

    Reserved for future implementation.
    """

    detected: bool = False
    confidence: float = 0.0
    watermark_type: str | None = None  # "image", "audio", "video"
    version: str | None = None


class OpenTimestampsResult(BaseModel):
    """OpenTimestamps blockchain verification result.

    Uses Bitcoin blockchain for immutable, decentralized timestamp proofs.
    Does not require trust in any central authority.

    Reserved for future implementation.
    """

    verified: bool = False
    timestamp: datetime | None = None
    bitcoin_block_height: int | None = None
    bitcoin_block_hash: str | None = None
    merkle_root: str | None = None
    attestations: list[dict[str, Any]] = Field(default_factory=list)


class PlatformAIGC(BaseModel):
    """Platform-specific AI-Generated Content labels.

    Different platforms add their own AIGC markers when content is uploaded.
    This captures those platform-specific labels.
    """

    # TikTok AIGC fields (from embedded metadata)
    tiktok_aigc_label_type: int | None = None  # 2 = AI generated
    tiktok_video_id: str | None = None  # vid:xxx from Comment field
    tiktok_video_md5: str | None = None  # VidMd5 hash

    # TikTok Research API fields
    tiktok_api_video_tag_number: int | None = None  # 1 = creator labeled, 2 = auto-detected
    tiktok_api_video_tag_type: str | None = None  # "AIGC Type"

    # YouTube Data API v3 fields
    youtube_video_id: str | None = None
    youtube_contains_synthetic_media: bool | None = None  # status.containsSyntheticMedia

    @property
    def is_tiktok_ai_labeled(self) -> bool:
        """Check if TikTok marked this as AI-generated (embedded metadata)."""
        return self.tiktok_aigc_label_type == 2

    @property
    def is_tiktok_api_ai_labeled(self) -> bool:
        """Check if TikTok Research API indicates AI-generated."""
        return self.tiktok_api_video_tag_type == "AIGC Type"

    @property
    def is_youtube_ai_labeled(self) -> bool:
        """Check if YouTube API indicates AI-generated."""
        return self.youtube_contains_synthetic_media is True

    @property
    def has_tiktok_metadata(self) -> bool:
        """Check if this video has TikTok metadata."""
        return self.tiktok_video_id is not None

    @property
    def has_platform_ai_label(self) -> bool:
        """Check if any platform has labeled this as AI-generated."""
        return (
            self.is_tiktok_ai_labeled or self.is_tiktok_api_ai_labeled or self.is_youtube_ai_labeled
        )


class ProvenanceMetadata(BaseModel):
    """Provenance metadata for content authenticity."""

    c2pa: C2PAInfo = Field(default_factory=C2PAInfo)
    platform_aigc: PlatformAIGC = Field(default_factory=PlatformAIGC)

    # Watermark detection results
    watermarks: WatermarkResults = Field(default_factory=WatermarkResults)

    # Advanced verification (reserved for future implementation)
    tsa_timestamp: TSATimestamp | None = None
    synthid: SynthIDResult | None = None
    opentimestamps: OpenTimestampsResult | None = None

    @property
    def has_provenance(self) -> bool:
        """Check if any provenance information is available."""
        return (
            self.c2pa.has_c2pa
            or self.watermarks.has_watermark
            or (self.tsa_timestamp is not None and self.tsa_timestamp.verified)
            or (self.synthid is not None and self.synthid.detected)
            or (self.opentimestamps is not None and self.opentimestamps.verified)
        )

    @property
    def is_verified(self) -> bool:
        """Check if provenance is cryptographically verified."""
        return self.c2pa.validation_state == "Valid"
