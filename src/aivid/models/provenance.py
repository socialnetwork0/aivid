"""Provenance metadata models (C2PA)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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

    # Generator info
    claim_generator: str | None = None
    software_agent: str | None = None

    # Signature info
    issuer: str | None = None
    signer_name: str | None = None
    cert_serial_number: str | None = None
    signature_time: datetime | None = None

    # AI-specific
    digital_source_type: str | None = None

    # Actions
    actions: list[C2PAAction] = Field(default_factory=list)

    # Ingredients (for edited content)
    ingredient_count: int = 0
    ingredients: list[dict[str, Any]] = Field(default_factory=list)

    # Validation
    validation_state: str | None = None  # "Valid", "Invalid", etc.
    validation_errors: list[str] = Field(default_factory=list)

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


class ProvenanceMetadata(BaseModel):
    """Provenance metadata for content authenticity."""

    c2pa: C2PAInfo = Field(default_factory=C2PAInfo)

    # Future: SynthID, Meta Video Seal, etc.
    # synthid: SynthIDInfo | None = None
    # meta_seal: MetaSealInfo | None = None

    @property
    def has_provenance(self) -> bool:
        """Check if any provenance information is available."""
        return self.c2pa.has_c2pa

    @property
    def is_verified(self) -> bool:
        """Check if provenance is cryptographically verified."""
        return self.c2pa.validation_state == "Valid"
