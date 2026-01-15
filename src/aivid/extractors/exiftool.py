"""ExifTool metadata extractor for XMP, EXIF, IPTC."""

import contextlib
import json
import shutil
import subprocess
from datetime import datetime
from typing import Any, ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import VideoMetadata


class ExifToolExtractor(BaseExtractor):
    """Extract metadata using ExifTool.

    ExifTool extracts comprehensive metadata including:
    - XMP: CreateDate, ModifyDate, Creator, etc.
    - EXIF: DateTimeOriginal, Make, Model, GPS, etc.
    - IPTC: Keywords, Copyright, AI fields (2025.1)

    This extractor provides "content creation time" which is independent
    of filesystem timestamps (download/copy time).

    Install: brew install exiftool (macOS) or apt install libimage-exiftool-perl (Linux)
    """

    name: ClassVar[str] = "exiftool"
    priority: ClassVar[int] = 15  # After FFprobe (10), before C2PA (20)

    # ExifTool date formats
    DATE_FORMATS = [
        "%Y:%m:%d %H:%M:%S%z",  # 2024:01:15 12:30:45+08:00
        "%Y:%m:%d %H:%M:%S",  # 2024:01:15 12:30:45
        "%Y-%m-%dT%H:%M:%S%z",  # ISO format with TZ
        "%Y-%m-%dT%H:%M:%S",  # ISO format
        "%Y:%m:%d %H:%M:%S.%f%z",  # With microseconds and TZ
        "%Y:%m:%d %H:%M:%S.%f",  # With microseconds
    ]

    @classmethod
    def is_available(cls) -> bool:
        """Check if exiftool is available."""
        return shutil.which("exiftool") is not None

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Extract metadata using exiftool."""
        exif_data = self._run_exiftool(path)
        if not exif_data:
            return

        # Store raw data
        metadata.raw.exiftool = exif_data

        # Parse into model
        self._parse_descriptive(exif_data, metadata)
        self._parse_iptc_ai(exif_data, metadata)
        self._parse_timestamps(exif_data, metadata)
        self._parse_platform_aigc(exif_data, metadata)

    def _run_exiftool(self, path: str) -> dict[str, Any]:
        """Run exiftool and return JSON output."""
        try:
            cmd = [
                "exiftool",
                "-json",
                "-n",  # Numeric output (no units)
                "-G1",  # Show group names
                "-s",  # Short tag names
                path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                if data and isinstance(data, list):
                    return data[0]  # ExifTool returns a list
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return {}

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse various date formats from ExifTool."""
        if not date_str:
            return None

        # Try known formats
        for fmt in self.DATE_FORMATS:
            with contextlib.suppress(ValueError):
                return datetime.strptime(str(date_str), fmt)

        # Fallback: try ISO format parsing
        with contextlib.suppress(ValueError, TypeError):
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))

        return None

    def _parse_descriptive(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse descriptive metadata from ExifTool output."""
        desc = metadata.descriptive

        # Title (various sources)
        desc.title = desc.title or (
            data.get("XMP:Title") or data.get("QuickTime:Title") or data.get("IPTC:ObjectName")
        )

        # Description
        desc.description = desc.description or (
            data.get("XMP:Description")
            or data.get("EXIF:ImageDescription")
            or data.get("IPTC:Caption-Abstract")
        )

        # Creator
        desc.creator = desc.creator or (
            data.get("XMP:Creator") or data.get("EXIF:Artist") or data.get("IPTC:By-line")
        )

        # Copyright
        desc.copyright = desc.copyright or (
            data.get("XMP:Rights") or data.get("EXIF:Copyright") or data.get("IPTC:CopyrightNotice")
        )

        # Software
        desc.software = desc.software or (data.get("XMP:CreatorTool") or data.get("EXIF:Software"))

        # Keywords
        keywords = data.get("XMP:Subject") or data.get("IPTC:Keywords")
        if keywords:
            if isinstance(keywords, list):
                desc.keywords.extend(k for k in keywords if k not in desc.keywords)
            elif isinstance(keywords, str):
                for k in keywords.split(","):
                    k = k.strip()
                    if k and k not in desc.keywords:
                        desc.keywords.append(k)

        # GPS
        if not desc.has_gps:
            desc.gps_latitude = data.get("EXIF:GPSLatitude")
            desc.gps_longitude = data.get("EXIF:GPSLongitude")
            desc.gps_altitude = data.get("EXIF:GPSAltitude")

        # Camera
        desc.camera_make = desc.camera_make or data.get("EXIF:Make")
        desc.camera_model = desc.camera_model or data.get("EXIF:Model")

    def _parse_iptc_ai(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse IPTC 2025.1 AI fields."""
        ai = metadata.descriptive.iptc_ai

        # IPTC AI Content Declaration fields (check both XMP and IPTC namespaces)
        ai.ai_system_used = data.get("XMP:AISystemUsed") or data.get("IPTC:AISystemUsed")
        ai.ai_system_version = data.get("XMP:AISystemVersion")
        ai.ai_prompt_info = data.get("XMP:AIPromptInfo")
        ai.ai_prompt_writer_name = data.get("XMP:AIPromptWriterName")
        ai.ai_training_mining_usage = data.get("XMP:AITrainingMiningUsage")

        # AI Generated flag
        ai_gen = data.get("XMP:AIGenerated")
        if ai_gen is not None:
            if isinstance(ai_gen, bool):
                ai.ai_generated = ai_gen
            elif isinstance(ai_gen, int):
                ai.ai_generated = bool(ai_gen)
            elif isinstance(ai_gen, str):
                ai.ai_generated = ai_gen.lower() == "true"

        # If IPTC AI fields detected, update AI detection
        if ai.ai_system_used or ai.ai_generated:
            self._update_ai_detection(metadata)

    def _parse_timestamps(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse timestamps from ExifTool output."""
        desc = metadata.descriptive

        # Creation date priority: XMP > EXIF > QuickTime
        create_keys = [
            "XMP:CreateDate",
            "XMP:DateCreated",
            "EXIF:DateTimeOriginal",
            "EXIF:CreateDate",
            "QuickTime:CreateDate",
            "QuickTime:CreationDate",
        ]

        for key in create_keys:
            if key in data:
                parsed = self._parse_date(str(data[key]))
                if parsed:
                    # Only update if not already set by higher priority source
                    if not desc.creation_timestamp.value:
                        desc.creation_timestamp.value = parsed
                        desc.creation_timestamp.source = "exiftool"
                        desc.creation_timestamp.raw_value = str(data[key])
                        desc.creation_date = parsed
                    break

        # Modification date
        modify_keys = [
            "XMP:ModifyDate",
            "EXIF:ModifyDate",
            "QuickTime:ModifyDate",
        ]

        for key in modify_keys:
            if key in data:
                parsed = self._parse_date(str(data[key]))
                if parsed:
                    if not desc.modification_timestamp.value:
                        desc.modification_timestamp.value = parsed
                        desc.modification_timestamp.source = "exiftool"
                        desc.modification_timestamp.raw_value = str(data[key])
                        desc.modification_date = parsed
                    break

    def _parse_platform_aigc(self, data: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse platform-specific AIGC labels (TikTok, etc.)."""
        platform = metadata.provenance.platform_aigc

        # TikTok AIGC fields (stored in Keys: namespace)
        aigc_info = data.get("Keys:AigcInfo")
        if aigc_info:
            # Parse JSON: {"aigc_label_type":2}
            if isinstance(aigc_info, str):
                try:
                    import json

                    aigc_data = json.loads(aigc_info)
                    platform.tiktok_aigc_label_type = aigc_data.get("aigc_label_type")
                except json.JSONDecodeError:
                    pass
            elif isinstance(aigc_info, dict):
                platform.tiktok_aigc_label_type = aigc_info.get("aigc_label_type")

        # TikTok video ID from Comment field (vid:xxx)
        comment = data.get("Keys:Comment")
        if comment and isinstance(comment, str) and comment.startswith("vid:"):
            platform.tiktok_video_id = comment[4:]  # Remove "vid:" prefix

        # TikTok video MD5
        vid_md5 = data.get("Keys:VidMd5")
        if vid_md5:
            platform.tiktok_video_md5 = vid_md5

        # Update AI detection if TikTok AIGC label found
        if platform.is_tiktok_ai_labeled:
            self._update_ai_from_tiktok(metadata)

    def _update_ai_from_tiktok(self, metadata: VideoMetadata) -> None:
        """Update AI detection based on TikTok AIGC label."""
        ai = metadata.ai_detection
        platform = metadata.provenance.platform_aigc

        ai.is_ai_generated = True
        ai.add_signal(
            "tiktok_aigc",
            True,
            0.95,
            f"TikTok AIGC label: aigc_label_type={platform.tiktok_aigc_label_type}",
            is_fact=True,  # Direct platform metadata
        )

    def _update_ai_detection(self, metadata: VideoMetadata) -> None:
        """Update AI detection based on IPTC fields."""
        ai_info = metadata.descriptive.iptc_ai
        ai = metadata.ai_detection

        if ai_info.ai_generated:
            ai.is_ai_generated = True
            ai.add_signal(
                "iptc_ai_generated",
                True,
                0.95,
                "IPTC AIGenerated flag is true",
            )

        if ai_info.ai_system_used:
            ai.add_signal(
                "iptc_ai_system",
                True,
                0.9,
                f"IPTC AISystemUsed: {ai_info.ai_system_used}",
            )
            if not ai.generator_raw:
                ai.generator_raw = ai_info.ai_system_used
