"""JSON output formatter."""

import json
from typing import Any

from aivid.models import VideoMetadata


def format_json(metadata: VideoMetadata, indent: int = 2) -> str:
    """Format metadata as JSON string.

    Args:
        metadata: VideoMetadata object
        indent: JSON indentation level

    Returns:
        JSON formatted string
    """
    return metadata.model_dump_json(indent=indent)


def format_json_list(metadata_list: list[VideoMetadata], indent: int = 2) -> str:
    """Format multiple metadata objects as JSON array.

    Args:
        metadata_list: List of VideoMetadata objects
        indent: JSON indentation level

    Returns:
        JSON array formatted string
    """
    data = [m.model_dump(mode="json") for m in metadata_list]
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def to_dict(metadata: VideoMetadata) -> dict[str, Any]:
    """Convert metadata to dictionary.

    Args:
        metadata: VideoMetadata object

    Returns:
        Dictionary representation
    """
    return metadata.model_dump(mode="json")
