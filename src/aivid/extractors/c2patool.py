"""C2PA metadata extractor using c2patool CLI (fallback)."""

import contextlib
import json
import shutil
import subprocess
from datetime import datetime
from typing import Any, ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import C2PAAction, VideoMetadata
from aivid.models.ai import AI_GENERATORS, SIGNING_AUTHORITIES


class C2PAToolExtractor(BaseExtractor):
    """Extract C2PA Content Credentials using c2patool CLI.

    This is a fallback extractor when c2pa-python is not available.
    Requires c2patool to be installed: cargo install c2patool

    Note: This extractor has lower priority than C2PAExtractor,
    so it will only be used if c2pa-python is not installed.
    """

    name: ClassVar[str] = "c2patool"
    priority: ClassVar[int] = 25  # Lower priority than c2pa-python

    @classmethod
    def is_available(cls) -> bool:
        """Check if c2patool CLI is available."""
        return shutil.which("c2patool") is not None

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Extract C2PA metadata using c2patool CLI."""
        try:
            result = subprocess.run(
                ["c2patool", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout:
                manifest_data = json.loads(result.stdout)
                self._parse_manifest(manifest_data, metadata)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

    def _parse_manifest(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse C2PA manifest data from c2patool output."""
        c2pa = metadata.provenance.c2pa

        # Skip if c2pa-python already extracted
        if c2pa.has_c2pa and c2pa.source == "c2pa-python":
            return

        c2pa.has_c2pa = True
        c2pa.source = "c2patool"

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


def check_c2patool_available() -> bool:
    """Check if c2patool CLI is available."""
    return C2PAToolExtractor.is_available()


def sign_with_c2pa(
    input_path: str,
    manifest_path: str,
    output_path: str,
    certificate_path: str | None = None,
    private_key_path: str | None = None,
) -> tuple[bool, str]:
    """Sign a file with C2PA manifest using c2patool.

    Args:
        input_path: Path to the input media file
        manifest_path: Path to the manifest JSON file
        output_path: Path for the signed output file
        certificate_path: Optional path to signing certificate
        private_key_path: Optional path to private key

    Returns:
        Tuple of (success: bool, message: str)
    """
    import os

    if not check_c2patool_available():
        return False, "c2patool not found. Install: cargo install c2patool"

    if not os.path.exists(input_path):
        return False, f"Input file not found: {input_path}"

    if not os.path.exists(manifest_path):
        return False, f"Manifest file not found: {manifest_path}"

    cmd = ["c2patool", input_path, "-m", manifest_path, "-o", output_path]

    # Add certificate and key if provided
    if certificate_path and private_key_path:
        if not os.path.exists(certificate_path):
            return False, f"Certificate file not found: {certificate_path}"
        if not os.path.exists(private_key_path):
            return False, f"Private key file not found: {private_key_path}"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True, f"Successfully signed: {output_path}"
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return False, f"Signing failed: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "Signing timed out after 120 seconds"
    except Exception as e:
        return False, f"Signing error: {e}"
