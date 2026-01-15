"""Tests for ExifTool extractor."""

from datetime import datetime

import pytest

from aivid.extractors.exiftool import ExifToolExtractor
from aivid.models import FileInfo, VideoMetadata


class TestExifToolExtractor:
    """Test ExifToolExtractor."""

    def test_is_available(self):
        """Test availability check returns a boolean."""
        result = ExifToolExtractor.is_available()
        assert isinstance(result, bool)

    def test_priority(self):
        """Test extractor priority is between FFprobe and C2PA."""
        assert ExifToolExtractor.priority == 15
        assert ExifToolExtractor.name == "exiftool"

    def test_parse_date_iso_format(self):
        """Test ISO date format parsing."""
        extractor = ExifToolExtractor()
        result = extractor._parse_date("2024-01-15T12:30:45+00:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12

    def test_parse_date_exif_format(self):
        """Test EXIF date format parsing."""
        extractor = ExifToolExtractor()
        result = extractor._parse_date("2024:01:15 12:30:45")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_with_timezone(self):
        """Test date parsing with timezone."""
        extractor = ExifToolExtractor()
        result = extractor._parse_date("2024:01:15 12:30:45+08:00")
        assert result is not None
        assert result.tzinfo is not None

    def test_parse_date_invalid(self):
        """Test invalid date returns None."""
        extractor = ExifToolExtractor()
        assert extractor._parse_date("invalid") is None
        assert extractor._parse_date(None) is None
        assert extractor._parse_date("") is None

    def test_parse_date_with_z_suffix(self):
        """Test date with Z suffix (UTC)."""
        extractor = ExifToolExtractor()
        result = extractor._parse_date("2024-01-15T12:30:45Z")
        assert result is not None

    def test_parse_iptc_ai_fields(self):
        """Test IPTC AI field parsing."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        # Simulate ExifTool output
        exif_data = {
            "XMP:AISystemUsed": "OpenAI DALL-E 3",
            "XMP:AIGenerated": True,
            "XMP:AIPromptInfo": "A beautiful sunset over mountains",
            "XMP:AISystemVersion": "3.0",
        }

        extractor._parse_iptc_ai(exif_data, metadata)

        assert metadata.descriptive.iptc_ai.ai_system_used == "OpenAI DALL-E 3"
        assert metadata.descriptive.iptc_ai.ai_generated is True
        assert (
            metadata.descriptive.iptc_ai.ai_prompt_info
            == "A beautiful sunset over mountains"
        )
        assert metadata.descriptive.iptc_ai.ai_system_version == "3.0"

    def test_parse_iptc_ai_updates_detection(self):
        """Test that IPTC AI fields update AI detection."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        exif_data = {
            "XMP:AISystemUsed": "Midjourney",
            "XMP:AIGenerated": True,
        }

        extractor._parse_iptc_ai(exif_data, metadata)

        assert metadata.ai_detection.is_ai_generated is True
        assert "iptc_ai_generated" in metadata.ai_detection.signals
        assert "iptc_ai_system" in metadata.ai_detection.signals

    def test_parse_iptc_ai_string_boolean(self):
        """Test parsing AIGenerated as string 'true'."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        exif_data = {"XMP:AIGenerated": "true"}
        extractor._parse_iptc_ai(exif_data, metadata)
        assert metadata.descriptive.iptc_ai.ai_generated is True

    def test_parse_timestamps(self):
        """Test timestamp parsing from ExifTool output."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        exif_data = {
            "XMP:CreateDate": "2024:06:15 10:30:00",
            "XMP:ModifyDate": "2024:06:16 14:00:00",
        }

        extractor._parse_timestamps(exif_data, metadata)

        assert metadata.descriptive.creation_timestamp.value is not None
        assert metadata.descriptive.creation_timestamp.source == "exiftool"
        assert metadata.descriptive.creation_date.year == 2024
        assert metadata.descriptive.creation_date.month == 6

    def test_parse_descriptive_metadata(self):
        """Test descriptive metadata parsing."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        exif_data = {
            "XMP:Title": "Test Video",
            "XMP:Creator": "Test Author",
            "XMP:Description": "A test description",
            "XMP:Rights": "Copyright 2024",
            "XMP:CreatorTool": "Adobe Premiere Pro",
            "XMP:Subject": ["keyword1", "keyword2"],
        }

        extractor._parse_descriptive(exif_data, metadata)

        assert metadata.descriptive.title == "Test Video"
        assert metadata.descriptive.creator == "Test Author"
        assert metadata.descriptive.description == "A test description"
        assert metadata.descriptive.copyright == "Copyright 2024"
        assert metadata.descriptive.software == "Adobe Premiere Pro"
        assert "keyword1" in metadata.descriptive.keywords
        assert "keyword2" in metadata.descriptive.keywords

    def test_parse_gps_coordinates(self):
        """Test GPS coordinate parsing."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        exif_data = {
            "EXIF:GPSLatitude": 37.7749,
            "EXIF:GPSLongitude": -122.4194,
            "EXIF:GPSAltitude": 10.5,
        }

        extractor._parse_descriptive(exif_data, metadata)

        assert metadata.descriptive.gps_latitude == 37.7749
        assert metadata.descriptive.gps_longitude == -122.4194
        assert metadata.descriptive.gps_altitude == 10.5
        assert metadata.descriptive.has_gps is True

    def test_timestamp_priority_not_overwrite(self):
        """Test that lower priority timestamps don't overwrite higher priority ones."""
        extractor = ExifToolExtractor()
        file_info = FileInfo(
            path="/test/video.mp4",
            filename="video.mp4",
            extension=".mp4",
            size_bytes=1000,
        )
        metadata = VideoMetadata(file_info=file_info)

        # Pre-set a timestamp with higher priority source
        metadata.descriptive.creation_timestamp.value = datetime(2024, 1, 1, 0, 0, 0)
        metadata.descriptive.creation_timestamp.source = "c2pa"

        exif_data = {
            "XMP:CreateDate": "2024:06:15 10:30:00",
        }

        extractor._parse_timestamps(exif_data, metadata)

        # Should not be overwritten
        assert metadata.descriptive.creation_timestamp.source == "c2pa"
        assert metadata.descriptive.creation_timestamp.value.year == 2024
        assert metadata.descriptive.creation_timestamp.value.month == 1


class TestTimestampInfo:
    """Test TimestampInfo model."""

    def test_default_values(self):
        """Test default values are None."""
        from aivid.models.descriptive import TimestampInfo

        ts = TimestampInfo()
        assert ts.value is None
        assert ts.source is None
        assert ts.raw_value is None


class TestIPTCAIInfo:
    """Test IPTCAIInfo model."""

    def test_default_values(self):
        """Test default values are None."""
        from aivid.models.descriptive import IPTCAIInfo

        ai = IPTCAIInfo()
        assert ai.ai_system_used is None
        assert ai.ai_generated is None
        assert ai.ai_prompt_info is None

    def test_all_fields(self):
        """Test all fields can be set."""
        from aivid.models.descriptive import IPTCAIInfo

        ai = IPTCAIInfo(
            ai_system_used="DALL-E 3",
            ai_system_version="3.0",
            ai_prompt_info="A sunset",
            ai_prompt_writer_name="Test User",
            ai_generated=True,
            ai_training_mining_usage="allowed",
        )
        assert ai.ai_system_used == "DALL-E 3"
        assert ai.ai_system_version == "3.0"
        assert ai.ai_generated is True


class TestProvenancePlaceholders:
    """Test placeholder models for future verification."""

    def test_tsa_timestamp_defaults(self):
        """Test TSATimestamp default values."""
        from aivid.models.provenance import TSATimestamp

        tsa = TSATimestamp()
        assert tsa.verified is False
        assert tsa.timestamp is None

    def test_synthid_result_defaults(self):
        """Test SynthIDResult default values."""
        from aivid.models.provenance import SynthIDResult

        synthid = SynthIDResult()
        assert synthid.detected is False
        assert synthid.confidence == 0.0

    def test_opentimestamps_result_defaults(self):
        """Test OpenTimestampsResult default values."""
        from aivid.models.provenance import OpenTimestampsResult

        ots = OpenTimestampsResult()
        assert ots.verified is False
        assert ots.bitcoin_block_height is None

    def test_provenance_has_provenance_extended(self):
        """Test has_provenance property with new verification types."""
        from aivid.models.provenance import (
            ProvenanceMetadata,
            SynthIDResult,
            TSATimestamp,
        )

        prov = ProvenanceMetadata()
        assert prov.has_provenance is False

        # Test with TSA
        prov.tsa_timestamp = TSATimestamp(verified=True)
        assert prov.has_provenance is True

        # Reset and test with SynthID
        prov = ProvenanceMetadata()
        prov.synthid = SynthIDResult(detected=True)
        assert prov.has_provenance is True


@pytest.mark.skipif(
    not ExifToolExtractor.is_available(),
    reason="exiftool not available",
)
class TestExifToolIntegration:
    """Integration tests requiring exiftool."""

    def test_run_exiftool_empty_on_missing_file(self):
        """Test that missing file returns empty dict."""
        extractor = ExifToolExtractor()
        result = extractor._run_exiftool("/nonexistent/file.mp4")
        assert result == {}
