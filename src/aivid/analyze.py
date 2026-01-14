"""Core analysis functions."""

import os
import warnings
from datetime import datetime

from aivid.extractors import get_available_extractors
from aivid.models import FileInfo, VideoMetadata
from aivid.utils.container import (
    MP4_EXTENSIONS,
    extract_strings,
    filter_interesting_strings,
    parse_mp4_boxes,
)


def get_file_info(path: str) -> FileInfo:
    """Get basic file information.

    Args:
        path: Path to the file

    Returns:
        FileInfo object with file details
    """
    stat = os.stat(path)

    # Get timestamps
    modified = datetime.fromtimestamp(stat.st_mtime)
    accessed = datetime.fromtimestamp(stat.st_atime)

    # st_birthtime is macOS-only
    created = None
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime:
        created = datetime.fromtimestamp(birthtime)

    return FileInfo(
        path=os.path.abspath(path),
        filename=os.path.basename(path),
        extension=os.path.splitext(path)[1].lower(),
        size_bytes=stat.st_size,
        created=created,
        modified=modified,
        accessed=accessed,
    )


def analyze_file(path: str, full: bool = False) -> VideoMetadata:
    """Analyze a video file and extract all available metadata.

    This is the main entry point for video analysis. It:
    1. Gets basic file information
    2. Runs all available extractors (FFprobe, C2PA, etc.)
    3. Parses container structure (for MP4/MOV)
    4. Extracts interesting strings (if full mode)
    5. Returns a unified VideoMetadata object

    Args:
        path: Path to the video file
        full: If True, extract all available metadata including raw strings

    Returns:
        VideoMetadata object with all extracted information

    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # Get basic file info
    file_info = get_file_info(path)

    # Create metadata object
    metadata = VideoMetadata(file_info=file_info)

    # Run all available extractors
    for extractor in get_available_extractors():
        try:
            extractor.extract(path, metadata)
        except Exception as e:
            warnings.warn(f"{extractor.name} extraction failed: {e}", stacklevel=2)

    # Parse MP4 box structure for MP4/MOV files
    if file_info.extension in MP4_EXTENSIONS:
        try:
            boxes = parse_mp4_boxes(path)
            metadata.raw.box_structure = boxes
        except Exception:
            pass

    # Extract interesting strings (for full mode)
    if full:
        try:
            raw_strings = extract_strings(path)
            metadata.raw.strings = filter_interesting_strings(raw_strings)
        except Exception:
            pass

    return metadata


def analyze_files(paths: list[str], full: bool = False) -> list[VideoMetadata]:
    """Analyze multiple video files.

    Args:
        paths: List of file paths
        full: If True, extract all available metadata

    Returns:
        List of VideoMetadata objects
    """
    results = []
    for path in paths:
        try:
            metadata = analyze_file(path, full=full)
            results.append(metadata)
        except Exception as e:
            warnings.warn(f"Failed to analyze {path}: {e}", stacklevel=2)
    return results


# Backward compatibility alias
extract = analyze_file
