"""
aivid - AI video toolkit

Detect, analyze, and work with AI-generated videos.
"""

from aivid.metadata import (
    analyze_file,
    check_c2patool_available,
    sign_with_c2pa,
)
from aivid.models import MetadataReport

__version__ = "0.1.0"
__all__ = [
    "analyze_file",
    "check_c2patool_available",
    "sign_with_c2pa",
    "MetadataReport",
    "__version__",
]
