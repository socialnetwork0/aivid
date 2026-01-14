"""Quiet output formatter - one-line summary."""

from aivid.models import VideoMetadata


def format_quiet(metadata: VideoMetadata) -> str:
    """Format metadata as one-line summary.

    Format: filename | duration | resolution | AI: yes/no (generator) | C2PA: yes/no
    """
    parts = []

    # Filename
    parts.append(metadata.filename)

    # Duration
    tech = metadata.technical
    parts.append(tech.duration_formatted)

    # Resolution
    video = tech.video
    if video.width and video.height:
        parts.append(f"{video.width}x{video.height}")
    else:
        parts.append("N/A")

    # AI status
    ai = metadata.ai_detection
    if ai.is_ai_generated:
        generator = ai.generator or "Unknown"
        parts.append(f"AI: yes ({generator})")
    else:
        parts.append("AI: no")

    # C2PA status
    c2pa = metadata.provenance.c2pa
    if c2pa.has_c2pa:
        parts.append("C2PA: yes")
    else:
        parts.append("C2PA: no")

    return " | ".join(parts)


def format_quiet_list(metadata_list: list[VideoMetadata]) -> str:
    """Format multiple metadata objects as one-line summaries.

    Args:
        metadata_list: List of VideoMetadata objects

    Returns:
        Multiple lines, one per file
    """
    return "\n".join(format_quiet(m) for m in metadata_list)
