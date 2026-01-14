"""Default output formatter - concise AI video analysis."""

from aivid.models import VideoMetadata


def format_default(metadata: VideoMetadata) -> str:
    """Format metadata as concise default output.

    Focuses on AI video analysis with:
    - AI generation info (generator, created time, title)
    - Video specs (duration, resolution, fps, size)
    - C2PA validation status
    """
    lines = []
    filename = metadata.filename

    lines.append("=" * 70)
    lines.append(f"File: {filename}")
    lines.append("=" * 70)

    # AI Generation section (if C2PA or AI detected)
    c2pa = metadata.provenance.c2pa
    ai = metadata.ai_detection

    if c2pa.has_c2pa or ai.is_ai_generated:
        lines.append("")
        lines.append("## AI GENERATION")

        # Generator
        generator = ai.generator or c2pa.claim_generator or "Unknown"
        lines.append(f"  Generator:    {generator}")

        # Creation time from signature
        if c2pa.signature_time:
            time_str = c2pa.signature_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"  Created:      {time_str}")

        # Title
        if c2pa.title:
            lines.append(f"  Title:        {c2pa.title}")

        # Digital source type
        if c2pa.digital_source_type:
            lines.append(f"  Source Type:  {c2pa.digital_source_type}")

        # Signer info
        if c2pa.issuer and c2pa.signer_name:
            lines.append(f"  Signed By:    {c2pa.issuer} ({c2pa.signer_name})")
        elif c2pa.issuer:
            lines.append(f"  Signed By:    {c2pa.issuer}")

    # Video Info section
    lines.append("")
    lines.append("## VIDEO INFO")

    tech = metadata.technical

    # Duration
    lines.append(f"  Duration:     {tech.duration_formatted}")

    # Resolution with aspect ratio
    video = tech.video
    if video.width and video.height:
        aspect = video.aspect_ratio
        if aspect:
            lines.append(f"  Resolution:   {video.width}x{video.height} ({aspect})")
        else:
            lines.append(f"  Resolution:   {video.width}x{video.height}")

    # Frame rate
    if video.fps:
        lines.append(f"  Frame Rate:   {video.fps:.0f} fps")

    # Size
    lines.append(f"  Size:         {metadata.file_info.size_human}")

    # C2PA Validation section (if C2PA detected)
    if c2pa.has_c2pa:
        lines.append("")
        lines.append("## C2PA VALIDATION")
        lines.append(f"  Status:       {c2pa.validation_state or 'Unknown'}")
        if c2pa.manifest_id:
            lines.append(f"  Manifest ID:  {c2pa.manifest_id}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)
