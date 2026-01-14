"""Pydantic models for aivid."""

from .ai import AI_GENERATORS, SIGNING_AUTHORITIES, AIDetectionResult, AISignal
from .descriptive import DescriptiveMetadata
from .file import FileInfo, format_size
from .provenance import C2PAAction, C2PAInfo, ProvenanceMetadata
from .raw import BoxInfo, RawMetadata
from .technical import AudioStream, TechnicalMetadata, VideoStream
from .video import VideoMetadata

__all__ = [
    # Main model
    "VideoMetadata",
    # Technical
    "TechnicalMetadata",
    "VideoStream",
    "AudioStream",
    # Descriptive
    "DescriptiveMetadata",
    # Provenance
    "ProvenanceMetadata",
    "C2PAInfo",
    "C2PAAction",
    # AI Detection
    "AIDetectionResult",
    "AISignal",
    "AI_GENERATORS",
    "SIGNING_AUTHORITIES",
    # File
    "FileInfo",
    "format_size",
    # Raw
    "RawMetadata",
    "BoxInfo",
]
