"""C2PA metadata extractor using c2pa-python library."""

import contextlib
import json
from datetime import datetime
from typing import Any, ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import C2PAAction, VideoMetadata
from aivid.models.ai import AI_GENERATORS, SIGNING_AUTHORITIES


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

        # Claim generator (from claim_generator_info list)
        claim_gen_info = manifest.get("claim_generator_info", [])
        if claim_gen_info and isinstance(claim_gen_info, list):
            first_gen = claim_gen_info[0]
            if isinstance(first_gen, dict):
                c2pa.claim_generator = first_gen.get("name")
            elif isinstance(first_gen, str):
                c2pa.claim_generator = first_gen

        # Signature info
        sig_info = manifest.get("signature_info", {})
        if sig_info:
            c2pa.issuer = sig_info.get("issuer")
            c2pa.signer_name = sig_info.get("common_name")
            c2pa.cert_serial_number = sig_info.get("cert_serial_number")

            # Parse signature time
            time_str = sig_info.get("time")
            if time_str:
                with contextlib.suppress(ValueError, TypeError):
                    # Handle ISO format with timezone
                    c2pa.signature_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

        # Parse assertions
        assertions = manifest.get("assertions", [])
        for assertion in assertions:
            label = assertion.get("label", "")
            assertion_data = assertion.get("data", {})

            if "c2pa.actions" in label:
                self._parse_actions(assertion_data, metadata)

        # Validation status
        c2pa.validation_state = data.get("validation_state")

        validation_status = data.get("validation_status", [])
        if validation_status:
            c2pa.validation_errors = [
                status.get("explanation", "") for status in validation_status if status
            ]

        # Ingredients
        ingredients = manifest.get("ingredients", [])
        c2pa.ingredient_count = len(ingredients)
        c2pa.ingredients = ingredients

        # Update AI detection based on C2PA info
        self._update_ai_detection(metadata)

    def _parse_actions(self, action_data: dict[str, Any], metadata: VideoMetadata) -> None:
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

            # Create action record
            c2pa_action = C2PAAction(
                action=action_type,
                software_agent=c2pa.software_agent,
                digital_source_type=source_type if source_type else None,
            )
            c2pa.actions.append(c2pa_action)

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
                if auth.lower() in c2pa.issuer.lower() and auth not in ai.signing_authorities:
                    ai.signing_authorities.append(auth)
