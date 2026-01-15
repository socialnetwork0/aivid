"""C2PA metadata extractor using c2pa-python library."""

import contextlib
import json
import re
from datetime import datetime
from typing import Any, ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import C2PAAction, VideoMetadata
from aivid.models.ai import AI_GENERATORS, SIGNING_AUTHORITIES

# Pattern to extract task_id from Sora title format: {task_id}_media.mp4
TASK_ID_PATTERN = re.compile(r"^([a-f0-9]{32})_media\.(mp4|webm|mov)$", re.IGNORECASE)


class C2PAExtractor(BaseExtractor):
    """Extract C2PA Content Credentials using the official c2pa-python library.

    This is the preferred C2PA extractor as it provides accurate parsing
    without requiring external binaries.

    Install: pip install c2pa-python
    """

    name: ClassVar[str] = "c2pa-python"
    priority: ClassVar[int] = 20

    @classmethod
    def is_available(cls) -> bool:
        """Check if c2pa-python is available."""
        try:
            from c2pa import Reader  # noqa: F401

            return True
        except ImportError:
            return False

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Extract C2PA metadata using c2pa-python."""
        try:
            from c2pa import Reader

            with Reader(path) as reader:
                manifest_json = reader.json()
                manifest_data = json.loads(manifest_json)
                self._parse_manifest(manifest_data, metadata)
        except Exception:
            # No C2PA data or parsing error
            pass

    def _parse_manifest(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse C2PA manifest data."""
        c2pa = metadata.provenance.c2pa
        c2pa.has_c2pa = True
        c2pa.source = "c2pa-python"

        # Store raw manifest
        metadata.raw.c2pa = data

        # Get active manifest
        active_id = data.get("active_manifest")
        if not active_id:
            return

        c2pa.manifest_id = active_id

        manifests = data.get("manifests", {})
        if active_id not in manifests:
            return

        manifest = manifests[active_id]

        # Basic info
        c2pa.title = manifest.get("title")
        c2pa.format = manifest.get("format")

        # Instance ID (XMP instance identifier)
        c2pa.instance_id = manifest.get("instanceId") or manifest.get("instance_id")

        # Extract task_id from title (e.g., "b1f75fc641144ddba74f8392297bc898_media.mp4")
        if c2pa.title:
            match = TASK_ID_PATTERN.match(c2pa.title)
            if match:
                c2pa.task_id = match.group(1)

        # Claim generator (from claim_generator_info list)
        claim_gen_info = manifest.get("claim_generator_info", [])
        if claim_gen_info and isinstance(claim_gen_info, list):
            first_gen = claim_gen_info[0]
            if isinstance(first_gen, dict):
                c2pa.claim_generator = first_gen.get("name")
                # Extract SDK version info (e.g., "org.contentauth.c2pa_rs": "0.67.1")
                for key, value in first_gen.items():
                    if key.startswith("org.contentauth.") or key == "version":
                        c2pa.claim_generator_product = key.replace(
                            "org.contentauth.", ""
                        )
                        c2pa.claim_generator_version = str(value)
                        break
            elif isinstance(first_gen, str):
                c2pa.claim_generator = first_gen

        # Signature info
        sig_info = manifest.get("signature_info", {})
        if sig_info:
            c2pa.issuer = sig_info.get("issuer")
            c2pa.signer_name = sig_info.get("common_name")
            c2pa.cert_serial_number = sig_info.get("cert_serial_number")
            c2pa.signature_algorithm = sig_info.get("alg")
            # cert_trusted from signature validation
            if "cert_trusted" in sig_info:
                c2pa.cert_trusted = sig_info.get("cert_trusted")

            # Parse signature time
            time_str = sig_info.get("time")
            if time_str:
                with contextlib.suppress(ValueError, TypeError):
                    # Handle ISO format with timezone
                    c2pa.signature_time = datetime.fromisoformat(
                        time_str.replace("Z", "+00:00")
                    )

        # Parse assertions
        assertions = manifest.get("assertions", [])
        for assertion in assertions:
            label = assertion.get("label", "")
            assertion_data = assertion.get("data", {})

            if "c2pa.actions" in label:
                self._parse_actions(assertion_data, metadata)

        # Validation status
        c2pa.validation_state = data.get("validation_state")

        # Set claim_signature_valid based on validation_state
        if c2pa.validation_state == "Valid":
            c2pa.claim_signature_valid = True
        elif c2pa.validation_state:
            c2pa.claim_signature_valid = False

        validation_status = data.get("validation_status", [])
        if validation_status:
            c2pa.validation_errors = [
                status.get("explanation", "") for status in validation_status if status
            ]
            # Check for untrusted certificate in validation status
            for status in validation_status:
                if status and "untrusted" in str(status.get("code", "")).lower():
                    c2pa.cert_trusted = False
                    break
            # If no trust issues found and not already set, mark as trusted
            if c2pa.cert_trusted is None and c2pa.validation_state == "Valid":
                c2pa.cert_trusted = True

        # Extract timestamp authority info from signature_info
        if sig_info:
            tsa_info = sig_info.get("time_authority", {}) or sig_info.get("tsa", {})
            if tsa_info:
                c2pa.timestamp_validated = True
                c2pa.timestamp_responder = tsa_info.get("responder") or tsa_info.get(
                    "name"
                )
            elif c2pa.signature_time:
                # Has signature time but unknown if TSA validated
                c2pa.timestamp_validated = None

        # Build cert chain from issuer info
        if c2pa.issuer:
            # Try to extract chain components from issuer string
            c2pa.cert_chain = c2pa.issuer

        # Ingredients
        ingredients = manifest.get("ingredients", [])
        c2pa.ingredient_count = len(ingredients)
        c2pa.ingredients = ingredients

        # Infer generation_mode from ingredients and digital_source_type
        self._infer_generation_mode(c2pa)

        # Update AI detection based on C2PA info
        self._update_ai_detection(metadata)

    def _infer_generation_mode(self, c2pa: Any) -> None:
        """Infer generation mode from C2PA data.

        Determines if content is text2video, image2video, video2video, etc.
        based on ingredients and digital_source_type.
        """
        # If no AI generation marker, skip
        if not c2pa.digital_source_type:
            return

        if "trainedAlgorithmicMedia" not in c2pa.digital_source_type:
            return

        # Check ingredients to determine generation mode
        if c2pa.ingredient_count == 0:
            # No ingredients = pure generation from text prompt
            c2pa.generation_mode = "text2video"
        else:
            # Has ingredients - check what type
            has_image = False
            has_video = False
            for ingredient in c2pa.ingredients:
                # Check format or relationship type
                ing_format = ingredient.get("format", "").lower()
                relationship = ingredient.get("relationship", "").lower()

                if any(
                    x in ing_format for x in ["image", "jpeg", "jpg", "png", "webp"]
                ):
                    has_image = True
                if any(x in ing_format for x in ["video", "mp4", "webm", "mov"]):
                    has_video = True

                # Also check relationship field
                if "parentOf" in relationship or "inputTo" in relationship:
                    # This is a source ingredient
                    pass

            if has_video:
                c2pa.generation_mode = "video2video"
            elif has_image:
                c2pa.generation_mode = "image2video"
            else:
                # Has ingredients but can't determine type
                c2pa.generation_mode = "text2video"

    def _parse_actions(
        self, action_data: dict[str, Any], metadata: VideoMetadata
    ) -> None:
        """Parse C2PA actions assertion."""
        c2pa = metadata.provenance.c2pa
        actions_list = action_data.get("actions", [])

        for action in actions_list:
            action_type = action.get("action", "")

            # Extract software agent
            software_agent = action.get("softwareAgent")
            if software_agent:
                if isinstance(software_agent, dict):
                    c2pa.software_agent = software_agent.get("name")
                elif isinstance(software_agent, str):
                    c2pa.software_agent = software_agent

            # Extract digital source type
            source_type = action.get("digitalSourceType", "")
            if source_type:
                # Extract just the type name from URL if present
                if "/" in source_type:
                    source_type = source_type.split("/")[-1]
                c2pa.digital_source_type = source_type

            # Parse when timestamp
            when_time = None
            when_str = action.get("when")
            if when_str:
                with contextlib.suppress(ValueError, TypeError):
                    when_time = datetime.fromisoformat(
                        str(when_str).replace("Z", "+00:00")
                    )

            # Create action record
            c2pa_action = C2PAAction(
                action=action_type,
                software_agent=c2pa.software_agent,
                digital_source_type=source_type if source_type else None,
                when=when_time,
            )
            c2pa.actions.append(c2pa_action)

            # Update descriptive timestamp from C2PA (highest priority)
            if when_time and action_type in ("c2pa.created", "c2pa.published"):
                desc = metadata.descriptive
                # C2PA timestamps have highest priority
                if (
                    not desc.creation_timestamp.value
                    or desc.creation_timestamp.source != "c2pa"
                ):
                    desc.creation_timestamp.value = when_time
                    desc.creation_timestamp.source = "c2pa"
                    desc.creation_timestamp.raw_value = str(when_str)
                    desc.creation_date = when_time

    def _update_ai_detection(self, metadata: VideoMetadata) -> None:
        """Update AI detection based on C2PA info."""
        c2pa = metadata.provenance.c2pa
        ai = metadata.ai_detection

        # Check digital source type for AI generation
        if c2pa.is_ai_generated:
            ai.is_ai_generated = True
            ai.confidence = 1.0
            ai.add_signal(
                "c2pa_source_type",
                True,
                1.0,
                f"digitalSourceType: {c2pa.digital_source_type}",
            )

        # Identify generator from claim_generator or software_agent
        generator_name = c2pa.claim_generator or c2pa.software_agent
        if generator_name:
            ai.generator_raw = generator_name
            for key, value in AI_GENERATORS.items():
                if key.lower() in generator_name.lower():
                    ai.generator = value
                    ai.is_ai_generated = True
                    break

        # Identify signing authorities
        if c2pa.issuer:
            for auth in SIGNING_AUTHORITIES:
                if (
                    auth.lower() in c2pa.issuer.lower()
                    and auth not in ai.signing_authorities
                ):
                    ai.signing_authorities.append(auth)
