"""Utility functions for aivid."""

from aivid.models.file import format_size

from .container import (
    CONTAINER_BOXES,
    MP4_EXTENSIONS,
    extract_strings,
    filter_interesting_strings,
    parse_mp4_boxes,
)
from .deps import (
    check_all_dependencies,
    check_python_dependencies,
    check_system_dependencies,
    print_dependency_status,
)

__all__ = [
    # Formatting
    "format_size",
    # Dependency checking
    "check_system_dependencies",
    "check_python_dependencies",
    "check_all_dependencies",
    "print_dependency_status",
    # Container parsing
    "parse_mp4_boxes",
    "extract_strings",
    "filter_interesting_strings",
    "CONTAINER_BOXES",
    "MP4_EXTENSIONS",
]
