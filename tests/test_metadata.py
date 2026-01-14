"""Tests for metadata extraction."""

import pytest

from aivid import __version__, analyze_file
from aivid.models import MetadataReport
from aivid.utils import format_size, get_file_info


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_format_size():
    """Test human-readable size formatting."""
    assert format_size(0) == "0.00 B"
    assert format_size(1023) == "1023.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"


def test_metadata_report_defaults():
    """Test MetadataReport default values."""
    report = MetadataReport()
    assert report.file_path == ""
    assert report.file_info == {}
    assert report.c2pa_info == {}
    assert report.is_ai_generated is False
    assert report.ai_generator is None


def test_metadata_report_ai_detection():
    """Test MetadataReport AI detection properties."""
    report = MetadataReport(c2pa_info={"has_c2pa": True, "generator": "OpenAI Sora"})
    assert report.is_ai_generated is True
    assert report.ai_generator == "OpenAI Sora"


def test_get_file_info(tmp_path):
    """Test get_file_info with a temporary file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    info = get_file_info(str(test_file))

    assert info["filename"] == "test.txt"
    assert info["size_bytes"] == 11
    assert info["size_human"] == "11.00 B"
    assert info["extension"] == ".txt"


def test_analyze_file_not_found():
    """Test analyze_file raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        analyze_file("/nonexistent/file.mp4")


@pytest.mark.requires_ffprobe
def test_analyze_file_basic(tmp_path, has_ffprobe):
    """Test basic file analysis."""
    if not has_ffprobe:
        pytest.skip("ffprobe not available")

    # Create a minimal test file
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"\x00" * 100)

    report = analyze_file(str(test_file))

    assert isinstance(report, MetadataReport)
    assert report.file_info["filename"] == "test.mp4"
    assert report.file_info["extension"] == ".mp4"
