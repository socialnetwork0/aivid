"""
aivid - AI video toolkit

Detect, analyze, and work with AI-generated videos.
"""

from aivid.metadata import analyze_file
from aivid.models import MetadataReport

__version__ = "0.1.0"
__all__ = ["analyze_file", "MetadataReport", "__version__"]
