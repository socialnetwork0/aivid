"""aivid - AI Video Metadata Toolkit.

Detect, analyze, and work with AI-generated videos.

Usage:
    from aivid import analyze_file, VideoMetadata

    # Analyze a video file
    metadata = analyze_file("video.mp4")

    # Check AI generation
    if metadata.is_ai_generated:
        print(f"AI Generator: {metadata.ai_generator}")

    # Access C2PA info
    if metadata.has_c2pa:
        print(f"Signed by: {metadata.provenance.c2pa.issuer}")

    # Export as JSON
    print(metadata.model_dump_json())
"""

from aivid._version import __version__
from aivid.analyze import analyze_file, analyze_files, extract, get_file_info
from aivid.extractors import (
    check_c2patool_available,
    get_available_extractors,
    get_extractor_status,
    print_extractor_status,
    sign_with_c2pa,
)
from aivid.formatters import (
    format_c2pa,
    format_default,
    format_full,
    format_json,
    format_quiet,
    to_dict,
)
from aivid.models import (
    AIDetectionResult,
    AudioStream,
    C2PAInfo,
    DescriptiveMetadata,
    FileInfo,
    ProvenanceMetadata,
    RawMetadata,
    TechnicalMetadata,
    VideoMetadata,
    VideoStream,
)
from aivid.utils import (
    check_all_dependencies,
    print_dependency_status,
)

# Backward compatibility: MetadataReport is now VideoMetadata
MetadataReport = VideoMetadata

__all__ = [
    # Version
    "__version__",
    # Main functions
    "analyze_file",
    "analyze_files",
    "extract",
    "get_file_info",
    # Models
    "VideoMetadata",
    "MetadataReport",  # Deprecated alias
    "TechnicalMetadata",
    "VideoStream",
    "AudioStream",
    "DescriptiveMetadata",
    "ProvenanceMetadata",
    "C2PAInfo",
    "AIDetectionResult",
    "FileInfo",
    "RawMetadata",
    # Formatters
    "format_default",
    "format_full",
    "format_c2pa",
    "format_json",
    "format_quiet",
    "to_dict",
    # C2PA functions
    "check_c2patool_available",
    "sign_with_c2pa",
    # Extractor functions
    "get_available_extractors",
    "get_extractor_status",
    "print_extractor_status",
    # Dependency functions
    "check_all_dependencies",
    "print_dependency_status",
]
