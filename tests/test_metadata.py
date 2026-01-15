"""Tests for metadata extraction."""

import pytest

from aivid import __version__, analyze_file
from aivid.models import FileInfo, VideoMetadata
from aivid.utils import format_size


def test_version():
    """Test that version is defined and follows semver format."""
    assert __version__
    # Check semver format (x.y.z)
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_format_size():
    """Test human-readable size formatting."""
    assert format_size(0) == "0 B"
    assert format_size(1023) == "1023 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"


def test_video_metadata_defaults():
    """Test VideoMetadata default values."""
    file_info = FileInfo(
        path="/test/video.mp4",
        filename="video.mp4",
        extension=".mp4",
        size_bytes=1000,
    )
    metadata = VideoMetadata(file_info=file_info)

    assert metadata.path == "/test/video.mp4"
    assert metadata.filename == "video.mp4"
    assert metadata.is_ai_generated is False
    assert metadata.ai_generator is None
    assert metadata.has_c2pa is False


def test_video_metadata_ai_detection():
    """Test VideoMetadata AI detection properties."""
    file_info = FileInfo(
        path="/test/video.mp4",
        filename="video.mp4",
        extension=".mp4",
        size_bytes=1000,
    )
    metadata = VideoMetadata(file_info=file_info)
    metadata.ai_detection.is_ai_generated = True
    metadata.ai_detection.generator = "OpenAI Sora"

    assert metadata.is_ai_generated is True
    assert metadata.ai_generator == "OpenAI Sora"


def test_video_metadata_c2pa():
    """Test VideoMetadata C2PA detection."""
    file_info = FileInfo(
        path="/test/video.mp4",
        filename="video.mp4",
        extension=".mp4",
        size_bytes=1000,
    )
    metadata = VideoMetadata(file_info=file_info)
    metadata.provenance.c2pa.has_c2pa = True
    metadata.provenance.c2pa.issuer = "OpenAI"
    metadata.provenance.c2pa.digital_source_type = "trainedAlgorithmicMedia"

    assert metadata.has_c2pa is True
    assert metadata.provenance.c2pa.is_ai_generated is True


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

    metadata = analyze_file(str(test_file))

    assert isinstance(metadata, VideoMetadata)
    assert metadata.filename == "test.mp4"
    assert metadata.file_info.extension == ".mp4"
