"""Pydantic models for aivid."""

from .ai import AI_GENERATORS, SIGNING_AUTHORITIES, AIDetectionResult, AISignal
from .descriptive import DescriptiveMetadata
from .file import FileInfo, format_size
from .provenance import C2PAAction, C2PAInfo, PlatformAIGC, ProvenanceMetadata
from .raw import BoxInfo, RawMetadata
from .source import SourceInfo, SourcePlatform
from .technical import AudioStream, TechnicalMetadata, VideoStream
from .video import VideoMetadata
from .watermark import WatermarkDetection, WatermarkResults

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
    "PlatformAIGC",
    # AI Detection
    "AIDetectionResult",
    "AISignal",
    "AI_GENERATORS",
    "SIGNING_AUTHORITIES",
    # Source
    "SourceInfo",
    "SourcePlatform",
    # Watermark
    "WatermarkDetection",
    "WatermarkResults",
    # File
    "FileInfo",
    "format_size",
    # Raw
    "RawMetadata",
    "BoxInfo",
]
